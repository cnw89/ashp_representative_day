import streamlit as st
import pandas as pd
import numpy as np
from heatsource import Boiler, HeatPump

Text_FILENAME = 'Text_profiles.csv'
Psolar_FILENAME = 'Psolar_profiles.csv'
Build_FILENAME = 'building_properties.csv'
heating_source_map = {'Gas boiler' : Boiler, 'Heat pump': HeatPump}
profile_name_map = {'Monthly minimum' : 'min', 'Monthly average': 'mean'}
building_type_map = {'Pre-1950''s': 0, '1950''s-60''s': 1, '1970''s' : 2, '1980''s' : 3, '1990''s' : 4,'2000''s' : 5,'post-2010': 6}
insulation_map = {'None' : 0, 'A little' : 1, 'A lot' : 2}
day_time = [7, 23]

#ventilation loss function
f_vent_pow = lambda Tin, Tout, Vroom, Nreplace : 0.33 * Vroom * Nreplace * (Tin - Tout)

#base power from internal sources (assumed constant in time)
Pbase = 1000 #W

def setup_sidebar():
    
    st.sidebar.header('Inputs')

    st.sidebar.subheader('Comparison 1')
    source1 = st.sidebar.selectbox(
        'Heating source',
        heating_source_map.keys(),
        key='1'
    )

    house1 = st.sidebar.selectbox(
        'Building type',
        building_type_map.keys(),
        key='1'
    )

    insulation1 = st.sidebar.selectbox(
        'Extra Insulation and draft proofing',
        insulation_map.keys(),
        key='1'
    )

    st.sidebar.subheader('Comparison 2')
    source2 = st.sidebar.selectbox(
        'Heating source',
        heating_source_map.keys(),
        key='2',
        index=1
    )

    house2 = st.sidebar.selectbox(
        'Building type',
        building_type_map.keys(),
        key='2'
    )

    insulation2 = st.sidebar.selectbox(
        'Extra Insulation and draft proofing',
        insulation_map.keys(),
        key='2'
    )
    
    st.sidebar.subheader('Internal Temperature Settings')
    T_day = st.sidebar.slider(
        'Day time (7am - 11pm) setpoint (degC)',
        16.0, 26.0, 20.0, step=0.5
    )
    T_night = st.sidebar.slider(
        'Night time (11pm - 7am) setpoint (degC)',
        5.0, 22.0, 18.0, step=0.5
    )

    st.sidebar.subheader('External Temperature Settings')
    month = st.sidebar.slider(
        'Month',
        1, 12, 1
    )

    profile_name = st.sidebar.radio(
        'External temperature profile type',
        profile_name_map.keys()
    )
    #option to input boiler power if you know what it is?
    #not helpful if combi boiler...
    input_dict = {'source1' : heating_source_map[source1],
                  'house1' : building_type_map[house1],
                  'insulation1': insulation_map[insulation1],
                  'source2' : heating_source_map[source2],
                  'house2' : building_type_map[house2],
                  'insulation2': insulation_map[insulation2],
                  'T_setpoints1': [T_day, T_night],
                  'month': str(month),
                  'profile_name' : profile_name_map[profile_name]
                  }
    
    return input_dict

#st.cahce
def import_monthly_profiles():
    df_Text = pd.read_csv(Text_FILENAME, index_col=0, header=[0, 1], parse_dates=[0], infer_datetime_format=True)
    df_Psolar = pd.read_csv(Psolar_FILENAME, index_col=0, header=[0, 1], parse_dates=[0], infer_datetime_format=True)
    
    return df_Text, df_Psolar

def lookup_monthly_profiles(month, profile_name, location=None):
    
    df_Text, df_Psolar = import_monthly_profiles()
    
    return df_Text.loc[:, (profile_name, month)], df_Psolar.loc[:, (profile_name, month)]

#st.cahce
def import_building():
    df_build = pd.read_csv(Build_FILENAME, index_col=0, header=[0, 1])
    
    return df_build

def lookup_build_properties(building_type, insulation):

    df_build = import_building()
    return df_build.loc[building_type, :]

def calc_design_heatloss(Text_min, Tset_max, build_properties):

    Vroom, Nreplace, u1, u2, u3, k1, k2, k3 = build_properties.iloc[:].tolist()
    Pvent = f_vent_pow(Tset_max, Text_min, Vroom, Nreplace)
    u = 1/(1/u1 + 1/u2 + 1/u3)
    Pwalls = u * (Tset_max - Text_min)

    return Pvent + Pwalls

def process_inputs(input_dict):
    """
    look at source1 and source2 and do appropriate things...
    e.g. modify T_setpoints for heat pumps if night time temperature is too low
    and get inputs the user doesn't input, e.g. efficiency, power (based on loss)
    
    return a list of length 3, external temperature profile, then each entry a
    dictionary of inputs for that test case
    """
    
    build_properties1 = lookup_build_properties(input_dict['house1'], input_dict['insulation1'])
    build_properties2 = lookup_build_properties(input_dict['house2'], input_dict['insulation2'])

    df_Text, df_Psolar = lookup_monthly_profiles(input_dict['month'], input_dict['profile_name'], location=None)
    
    #Todo: some kind of check that the night time temperature is not too different?
    Tsetpoints1 = input_dict['T_setpoints1']
    Tsetpoints2 = Tsetpoints1

    Pdesign1 = calc_design_heatloss(min(df_Text.tolist()), max(Tsetpoints1), build_properties1)
    Pdesign2 = calc_design_heatloss(min(df_Text.tolist()), max(Tsetpoints2), build_properties2)
    source1 = input_dict['source1'](Pdesign=Pdesign1)
    source2 = input_dict['source2'](Pdesign=Pdesign2)

    d1 = {'case': 1, 'source': source1, 'build_properties': build_properties1, 'Tsetpoints': Tsetpoints1}
    d2 = {'case': 2, 'source': source2, 'build_properties': build_properties2, 'Tsetpoints': Tsetpoints2}
    common_inputs = [df_Text, df_Psolar]
    input_list = [d1, d2]

    return common_inputs, input_list

def run_test_case(df_Text, df_Psolar, case, source, build_properties, Tsetpoints):
    """
    returns test_case_df - dataframe with columns [time, Text, Tint, pow]
    """
    
    #prepare values
    dt = (df_Text.index[1] - df_Text.index[0]).seconds    
    Vroom, Nreplace, u1, u2, u3, k1, k2, k3 = build_properties.iloc[:].tolist()
    
    #initialize Temperatures
    Tin = Tsetpoints[1]
    T1 = Tin/3 + (2/3) * df_Text.iloc[0]
    T2 = (2/3)*Tin + (1/3) * df_Text.iloc[0]

    #prepare output
    
    df_out = pd.DataFrame(columns=[('Common', 'Outside Temp'), 
                                   ('Common', 'Set Temp'), 
                                   ('Common', 'Psolar'), 
                                   (f'Case {case}', 'Inside Temp'),
                                   (f'Case {case}',  'T1'),
                                   (f'Case {case}',  'T2'),
                                   (f'Case {case}',  'Psource'),
                                   (f'Case {case}',  'Pvent'),
                                   (f'Case {case}',  'Pbase')
                                   ], dtype=float,
                                   index=df_Text.index)

    for itime, (t, Text) in enumerate(df_Text.items()):
        
        #get time-dependent set point
        t2 = t.hour + t.minute/60

        if t2 < day_time[0] or t2 > day_time[1]:
            Tset = Tsetpoints[1]
        else:
            Tset = Tsetpoints[0]

        # determine heat input
        Psource = source.run(Tin, Text, Tset) 
        Pvent = f_vent_pow(Tin, Text, Vroom, Nreplace) 
        heatinput = Psource - Pvent + df_Psolar.iloc[itime] + Pbase
        
        #print(heatinput, Tin, Text, Tset, Vroom, Nreplace, df_Psolar.iloc[itime], Pbase)
        
        net_heatflow_3 = heatinput - u3*(Tin - T2)
        net_heatflow_2 = u3*(Tin - T2) - u2*(T2 - T1)
        net_heatflow_1 = u2*(T2 - T1) - u1*(T1 - Text)

        Tin += (net_heatflow_3 * dt) / k3
        T2 += (net_heatflow_2 * dt) / k2
        T1 += (net_heatflow_1 * dt) / k1    
        
        df_out.iloc[itime, :] = [Text, Tset, df_Psolar.iloc[itime], Tin, T1, T2, Psource, Pvent, Pbase]

    #st.dataframe(df_out)
    
    return df_out

def run_all_test_cases(common_inputs, input_list):
    """
    Call run_test_case on all entries in input_list
    Return list of test_case_df
    """
    
    case1 = run_test_case(*common_inputs, **input_list[0])
    case2 = run_test_case(*common_inputs, **input_list[1])

    results = pd.concat([case1, case2], axis=1)

    return results

def intro():
    """
    asdas
    """

    'Representative day comparison tool v2'

def print_plots(input_dict, input_list, results):
    
    columns = [('Common', 'Outside Temp'), 
                ('Common', 'Set Temp'), 
                ('Case 1', 'Inside Temp'),
                ('Case 2', 'Inside Temp')]
                
    st.line_chart(results.loc[:, columns])

    columns = [('Common', 'Psolar'), 
                ('Case 1', 'Psource'),
                ('Case 1', 'Pvent'),
                ('Case 1', 'Pbase')]
                
    st.line_chart(results.loc[:, columns])

    columns = [('Common', 'Psolar'), 
                ('Case 2', 'Psource'),
                ('Case 2', 'Pvent'),
                ('Case 2', 'Pbase')]

    st.line_chart(results.loc[:, columns])

    columns = [('Common', 'Outside Temp'), 
                ('Common', 'Set Temp'), 
                ('Case 1', 'Inside Temp'),
                ('Case 1', 'T1'),
                ('Case 1', 'T2')]
                
    st.line_chart(results.loc[:, columns])

    columns = [('Common', 'Outside Temp'), 
                ('Common', 'Set Temp'), 
                ('Case 2', 'Inside Temp'),
                ('Case 2', 'T1'),
                ('Case 2', 'T2')]
                
    st.line_chart(results.loc[:, columns])

def appendix():
    """
    asdsad
    """

    'Our other assumptions'

# now do everything
input_dict = setup_sidebar()
common_inputs, input_list = process_inputs(input_dict)
results = run_all_test_cases(common_inputs, input_list)

intro()
print_plots(input_dict, input_list, results)
appendix()
