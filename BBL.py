# Eliot Abrams
# Food truck location choice

# Packages
import pandas as pd
import numpy as np
import sympy as sp
import datetime as dt
import scipy.optimize as opt

# Constants
NUM_TRUCKS = 3
COUNT_OF_EMPTY_STATES_REACHED = 0

# Sympy Variables (WOULD LIKE TO FIND A CLEANER WAY OF DECLARING AND
# STORING THESE)

# Intercept
intercept = sp.Symbol('intercept')

# Days
monday = sp.Symbol('monday')
tuesday = sp.Symbol('tuesday')
wednesday = sp.Symbol('wednesday')
thursday = sp.Symbol('thursday')
friday = sp.Symbol('friday')
saturday = sp.Symbol('saturday')
sunday = sp.Symbol('sunday')
days = [monday, tuesday, wednesday, thursday, friday, saturday, sunday]

# Quarters
q1 = sp.Symbol('q1')
q2 = sp.Symbol('q2')
q3 = sp.Symbol('q3')
q4 = sp.Symbol('q4')

quarters = [q1, q2, q3, q4]

# Locations
locationA = sp.Symbol('locationA')
locationB = sp.Symbol('locationB')
locationC = sp.Symbol('locationC')
locationO = sp.Symbol('locationO')

locations = pd.DataFrame(
    [locationA, locationB, locationC, locationO]).transpose()
locations.columns = ['A', 'B', 'C', 'O']

# Other variables
high_historic_count = sp.Symbol('high_historic_count')
high_historic_diversity = sp.Symbol('high_historic_diversity')
high_historic_freq = sp.Symbol('high_historic_freq')
high_current_count = sp.Symbol('high_current_count')
high_current_diversity = sp.Symbol('high_current_diversity')


# Create state as a vector (indicating location) storing an array (holding
# the variable values).
def make_states(location_data, making_probabilities, truck_types):
    """Function takes a dataset with Truck, Location, and Date (as a datetime variable)

    location_data = table with locations
    """

    # Complete panel if making the probabilities from the original location
    # data (else the panel is already complete by construction)
    if making_probabilities:
        location_data = location_data.pivot(
            index='Date', columns='Truck', values='Location')
        location_data = location_data.unstack().reset_index(
            name='Location').fillna('O')

    # Merge on truck types
    location_data = pd.merge(location_data, truck_types, on='Truck')

    # Create time variables
    location_data['Date'] = pd.to_datetime(location_data['Date'])
    location_data['Year_Plus_Week'] = location_data['Date'].dt.week + location_data['Date'].dt.year
    location_data['Day_Of_Week'] = location_data['Date'].dt.dayofweek
    location_data['Quarter'] = location_data['Date'].dt.quarter

    # Find the number and diversity of trucks at each location in each week
    # Form the pivot table
    grouped_by_year_plus_week_location = location_data.groupby(['Year_Plus_Week', 'Location'])
    joint_state_variables = grouped_by_year_plus_week_location.Type.agg(['count', 'nunique']).reset_index(
        ['Location', 'Year_Plus_Week']).rename(columns={'count': 'Count', 'nunique': 'Num_Unique'})
    joint_state_variables = pd.pivot_table(joint_state_variables,
                                           values=['Count', 'Num_Unique'],
                                           index='Year_Plus_Week',
                                           columns='Location').fillna(0).reset_index(['Year_Plus_Week', 'Count', 'Num_Unique'])

    # Collapse the multiple indices
    joint_state_variables.columns = pd.Index(
        [e[0] + e[1] for e in joint_state_variables.columns.tolist()])

    # Discretize the values (turn into dummy variables for now)
    joint_state_variables[joint_state_variables.ix[
        :, joint_state_variables.columns != 'Year_Plus_Week'] <= 4] = 0
    joint_state_variables[joint_state_variables.ix[
        :, joint_state_variables.columns != 'Year_Plus_Week'] > 4] = 1

    # Find the frequency with which each truck parks at each location_data
    # Form the pivot table
    truck_specific_state_variables = location_data.groupby(['Truck', 'Year_Plus_Week', 'Location'])['Date'].count(
    ).reset_index(['Truck', 'Location', 'Year_Plus_Week']).rename(columns={'Date': 'Truck_Weekly_Frequency'})

    # Create container table table
    container_table = truck_types.drop('Type', axis=1)
    temp = pd.DataFrame(list(locations.columns), columns=['Location'])
    container_table['key'] = 1
    temp['key'] = 1
    container_table = pd.merge(
        container_table, temp, on='key').ix[:, ('Truck', 'Location')]

    truck_specific_state_variables = truck_specific_state_variables.append(container_table).fillna(0)
    historic_truck_frequencies = pd.pivot_table(truck_specific_state_variables,
                                                values='Truck_Weekly_Frequency',
                                                index='Year_Plus_Week',
                                                columns=['Location', 'Truck']).fillna(0).reset_index()
    historic_truck_frequencies = historic_truck_frequencies[historic_truck_frequencies.Year_Plus_Week != 0]

    # Collapse the multiple indices
    historic_truck_frequencies.columns = pd.Index(
        [e[0] + str(e[1]) for e in historic_truck_frequencies.columns.tolist()])

    # Discretize the values (turn into dummy variables for now)
    historic_truck_frequencies[historic_truck_frequencies.ix[
        :, historic_truck_frequencies.columns != 'Year_Plus_Week'] > 0] = 1

    # If making the probability table merge these new variables onto the
    # location data on with a lag
    if making_probabilities:
        joint_state_variables.Year_Plus_Week += 1
        historic_truck_frequencies.Year_Plus_Week +=  1

    # Else just merge (note that observations that are not matched are being
    # dropped)
    location_data = pd.merge(
        location_data, joint_state_variables, on=['Year_Plus_Week'])
    location_data = pd.merge(
        location_data, historic_truck_frequencies, on=['Year_Plus_Week'])

    # Concatenate the created variables into a single state variable
    location_data = location_data.reindex_axis(
        sorted(location_data.columns), axis=1)

    state_variables = location_data.columns.tolist()
    state_variables.remove('Truck')
    state_variables.remove('Date')
    state_variables.remove('Location')
    state_variables.remove('Type')
    state_variables.remove('Year_Plus_Week')

    # Turning this into a dictionary isn't so neat... seems like storing dictionaries in a dataframe is recommended against
    # temp = joint_state_variables.to_dict(orient='records')
    # [OrderedDict(row) for i, row in df.iterrows()]
    location_data['State'] = location_data[state_variables].values.tolist()
    location_data.State = location_data.State.apply(tuple)

    return [location_data, state_variables]


# Calculate P(a_{it} | s_t) (WILL NEED TO REDO WITH A SEIVE LOGIT)
def find_probabilities(cleaned_location_data):

    # Find the number of times that each truck takes each action for each state
    numerator = cleaned_location_data.groupby(
        ['Truck', 'Location', 'State'])['Date'].count().reset_index()

    # Find the number of times that each state occurs
    denominator = cleaned_location_data.groupby(
        ['Truck', 'State'])['Date'].count().reset_index()

    # Calculate the probabilities
    probabilities = pd.merge(numerator, denominator, on=['Truck', 'State'])
    probabilities['Probability'] = probabilities.Date_x / probabilities.Date_y.apply(float)
    probabilities = probabilities.drop(['Date_x', 'Date_y'], 1)

    return probabilities


# Find vector of optimal action from probability list and state
def optimal_action(probability_list, state, truck_types):
    "Find optimal action from probability list, state, and truck id"

    # If the state is not present in the historic data then generate random
    # actions for the trucks
    if probability_list.loc[probability_list['State'] == state].empty:
        action_profile = generate_random_actions(truck_types)

        global COUNT_OF_EMPTY_STATES_REACHED
        COUNT_OF_EMPTY_STATES_REACHED += 1

    # If the state is present, find the optimal action using the Hotz-Miller
    # inversion
    else:
        comparison = probability_list.loc[probability_list['State'] == state]
        comparison['Shock'] = np.random.gumbel(
            loc=0.0, scale=1.0, size=len(comparison.index))
        comparison['Value'] = np.log(
            comparison['Probability']) + comparison['Shock']
        action_profile = comparison.sort('Value', ascending=False).drop_duplicates(
            'Truck').loc[:, ['Truck', 'Location', 'Shock']]

    return action_profile.sort('Truck')

# Find other action (as a function of the state and the strategy or build
# one for each strategy)
def generate_random_actions(truck_types):
    ""

    # Create a table with all possible actions for all trucks
    action_profile = truck_types.drop('Type', axis=1)
    temp = pd.DataFrame(list(locations.columns), columns=['Location'])
    action_profile['key'] = 1
    temp['key'] = 1
    comparison = pd.merge(action_profile, temp, on='key').ix[:, ('Truck', 'Location')]

    # Generate a random shock
    comparison['Shock'] = np.random.gumbel(
        loc=0.0, scale=1.0, size=len(comparison.index))

    # Return best action for truck (the economics is that I'm putting a null
    # prior over each action and so the action taken according to the
    # Hotz-Miller inversion is just the action with the highest shock value)
    action_profile = comparison.sort('Shock', ascending=False).drop_duplicates(
        'Truck').loc[:, ['Truck', 'Location', 'Shock']]

    return action_profile


def generate_certain_actions(certain_action, truck_types):
    ""

    action_profile = truck_types.drop('Type', axis=1)
    action_profile['Location'] = certain_action
    action_profile['Shock'] = np.random.gumbel(
        loc=0.0, scale=1.0, size=len(action_profile.index))

    return action_profile


# Calculate profit given current state and action profile WOULD REALLY
# LIKE TO GENERALIZE
def get_profit(location, truck, shock, df, current_variables, truck_types):

    # Add intercept, day of week indicator, quarter indicator, and shock. Day
    # of week is fed in as a 0-6, but quarter is fed in as 1-4 hence the
    # indexing adjustment for quarter
    profit = intercept + days[df.Day_Of_Week[0]] + \
        quarters[df.Quarter[0] - 1] + shock

    # Add historic count and diversity at chosen location
    count_var = 'Count' + location
    num_unique_var = 'Num_Unique' + location
    profit = profit + df[count_var][0] * high_historic_count + \
        df[num_unique_var][0] * high_historic_diversity

    # Add truck's historic frequency at chosen location
    historic_freq_var = location + str(truck)
    profit = profit + df[historic_freq_var][0] * high_historic_freq

    # Add current location variables
    profit = profit + locations[location][0] + current_variables.Count[location] * \
        high_current_count + \
        current_variables.Num_Unique[location] * high_current_diversity

    return profit


def create_profit_vector(state_variables, state, actions, truck_types):
    "Calculate profit given current state and action profile"

    # Put into data frame
    df = pd.DataFrame([state]).applymap(int)
    df.columns = state_variables

    # Create variables based on current actions and discretize
    actions = pd.merge(actions, truck_types, on='Truck')
    current_variables = actions.groupby(['Location'])['Type'].agg(
        ['count', 'nunique']).rename(columns={'count': 'Count', 'nunique': 'Num_Unique'})
    current_variables[current_variables <= 2] = 0
    current_variables[current_variables > 2] = 1

    # Create profit vector
    Profit_Vector = actions.drop(['Type'], 1)
    Profit_Vector['Profit'] = Profit_Vector.apply(lambda row: get_profit(
        row['Location'], row['Truck'], row['Shock'], df, current_variables, truck_types), axis=1)

    return Profit_Vector.drop(['Location', 'Shock'], 1)


# Update state
def update_state(state, action_sequence, Date, state_variables, truck_types):
    "Take the current state and recent history of actions and return the new state (clearing out the action sequence as necessary)"

    # If its the first day of the week, return the new state based on the
    # actions from the previous week and reset the sequence of actions that
    # we're keeping track of
    if pd.DatetimeIndex([Date])[0].dayofweek == 0:
        (Values, Labels) = make_states(location_data=action_sequence,
                                       making_probabilities=False, truck_types=truck_types)

        Content = pd.DataFrame([Values.State[0]])
        Content.columns = Labels

        Container = pd.DataFrame([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                                  0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]).transpose()
        Container.columns = state_variables

        new_state = tuple(pd.concat([Container, Content]).fillna(0).iloc[[1]].values[0])

        action_sequence = action_sequence.sort(columns=['Truck', 'Date'], ascending=False)
        action_sequence = action_sequence.drop_duplicates('Truck')

    # Else just update the day of week and quarter (I perfer to keep the state
    # as a tuple generally so that I don't accidently change it)
    else:
        new_state = list(state)
        new_state[state_variables.index('Day_Of_Week')] = pd.DatetimeIndex(
            [Date])[0].dayofweek
        new_state[state_variables.index('Quarter')] = pd.DatetimeIndex(
            [Date])[0].quarter
        new_state = tuple(new_state)

    return [new_state, action_sequence]


# Simulate a single path. ERROR: The first monday is not properly
# generating a variable... could be because I'm starting with a non-legit
# state
def simulate_single_path(probabilities, starting_state, starting_date,
                         periods, discount, state_variables, truck_id,
                         action_generator, specific_action, truck_types):
    ""

    # Set the initial values
    global NUM_TRUCKS
    current_date = dt.datetime.strptime(starting_date, '%Y-%m-%d')
    current_state = starting_state
    T = 0
    pdv_profits = np.zeros(NUM_TRUCKS)
    action_sequence = pd.DataFrame()

    while T < periods:
        # Find the optimal actions and add to the action sequence
        actions = optimal_action(probabilities, current_state, truck_types)

        # Replace specific truck's action with alternate strategy if requested
        if action_generator == 'Random':
            truck_actions = generate_random_actions(truck_types)
            truck_actions = truck_actions[truck_actions.Truck == truck_id]
            actions = actions[actions.Truck != truck_id]
            actions = actions.append(truck_actions)

        if action_generator == 'Specific':
            truck_actions = generate_certain_actions(specific_action, truck_types)
            truck_actions = truck_actions[truck_actions.Truck == truck_id]
            actions = actions[actions.Truck != truck_id]
            actions = actions.append(truck_actions)

        # Add the date to the current actions
        actions['Date'] = dt.datetime.strftime(current_date, '%Y-%m-%d')

        # Create the profit vector and add to the discounted sum of profits
        period_profits = create_profit_vector(state_variables=state_variables, state=current_state,
                                              actions=actions, truck_types=truck_types)
        pdv_profits += discount ** T * period_profits.Profit

        # Update state (appending current actions to action sequence)
        actions = actions.drop(['Shock'], axis=1)
        action_sequence = action_sequence.append(actions)

        (current_state, action_sequence) = update_state(state=current_state, action_sequence=action_sequence,
                                                        Date=dt.datetime.strftime(
                                                            current_date, '%Y-%m-%d'),
                                                        state_variables=state_variables, truck_types=truck_types)

        # Update counters
        T += 1
        current_date += dt.timedelta(days=1)

    return pd.DataFrame([period_profits.Truck, pdv_profits]).transpose()


# Average over N simulations of the valuation function and (currently)
# return only for single truck. This functions return is a bit unorthodox
# but significantly reduces calculations necessary. Could potential write
# a separate function to pick out specific truck
def find_value_function(probabilities, starting_state, starting_date, periods,
                        discount, state_variables, truck_id, action_generator,
                        specific_action, N, truck_types):
    ""

    global NUM_TRUCKS

    # Set initial values
    value_functions = np.zeros(NUM_TRUCKS)

    # Run N times
    for x in xrange(N):
        Results = simulate_single_path(probabilities=probabilities, starting_state=starting_state,
                                       starting_date=starting_date, periods=periods, discount=discount,
                                       state_variables=state_variables, truck_id=truck_id, action_generator=action_generator,
                                       specific_action=specific_action, truck_types=truck_types)

        value_functions += 1. / N * Results.Profit

    # Format results
    Step_One = pd.DataFrame([Results.Truck, value_functions]).transpose()

    return Step_One[Step_One.Truck == truck_id].Profit.get_values()[0]


# Build objective to maximize
def build_g(probabilities, starting_date, periods, discount, state_variables, N, truck_types, num_draws):

    # Create column with truck and strategy and starting state
    container_table = truck_types.drop('Type', axis=1)

    temp1 = pd.DataFrame(['Random'], columns=['action_generator'])
    temp2 = pd.DataFrame(list(locations.columns), columns=['specific_action'])
    temp2['action_generator'] = 'Specific'
    temp2 = temp2.append(temp1)

    container_table['key'] = 1
    temp2['key'] = 1
    container_table = pd.merge(container_table, temp2, on='key').ix[
        :, ('Truck', 'action_generator', 'specific_action')]
    container_table = container_table.fillna('')


    container_table['key'] = 1
    states = pd.DataFrame(probabilities[probabilities.Truck == 1].State)
    states['key'] = 1
    container_table = pd.merge(container_table, states, on='key').drop('key', axis=1)
    container_table = container_table.sample(num_draws)

    container_table['Value_Function_For_Other_Actions'] = container_table.apply(lambda row:
                    find_value_function(probabilities=probabilities, starting_state=row['State'],
                                        starting_date=starting_date, periods=periods, discount=discount,
                                        state_variables=state_variables, truck_id=row['Truck'],
                                        action_generator=row['action_generator'],
                                        specific_action=row['specific_action'],
                                        N=N, truck_types=truck_types), axis=1)

    container_table['Value_Function'] = container_table.apply(lambda row:
                    find_value_function(probabilities=probabilities, starting_state=row['State'],
                                        starting_date=starting_date, periods=periods, discount=discount,
                                        state_variables=state_variables, truck_id=row['Truck'],
                                        action_generator='Optimal',
                                        specific_action='',
                                        N=N, truck_types=truck_types), axis=1)

    container_table['g'] = container_table.Value_Function - \
        container_table.Value_Function_For_Other_Actions

    return container_table


# Estimate the parameters by maximizing the objective (later add a
# weighting vector)
def optimize(g):
    g['Terms'] = g.apply(lambda row: sp.Min(row.g, 0) ** 2, axis=1)
    objective = g.Terms.sum()
    variables = list(objective.atoms(sp.Symbol))

    def function(values):
        z = zip(variables, values)
        return float(objective.subs(z))

    initial_guess = np.ones(len(variables))

    return [opt.minimize(function, initial_guess, method='nelder-mead'), variables]




    