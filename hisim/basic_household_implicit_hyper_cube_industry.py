import inspect
import numpy as np
import os
from os import walk
import pandas as pd
import lhsmdu
from random import randrange
import sys
import simulator as sim
import components as cps
from components import occupancy
from components import weather
from components import pvs
from components import chp_system
from components import advanced_battery
from components import controller
from components import heat_pump_hplib
from components import hydrogen_generator
from components import demand_el
import pyDOE

from components import building
#from components import heat_pump
from components import sumbuilder
import simulator as sim
from cfg_automator import ConfigurationGenerator, SetupFunction, ComponentsConnection, ComponentsGrouping
import loadtypes

__authors__ = "Vitor Hugo Bellotto Zago"
__copyright__ = "Copyright 2021, the House Infrastructure Project"
__credits__ = ["Noah Pflugradt"]
__license__ = "MIT"
__version__ = "0.1"
__maintainer__ = "Vitor Hugo Bellotto Zago"
__email__ = "vitor.zago@rwth-aachen.de"
__status__ = "development"


####DIRTY CODE->nightshift
###Has to be automized an reworked
def basic_household_implicit_hyper_cube_industry(my_sim: sim.Simulator):
    my_setup_function = SetupFunction()
    my_setup_function.build(my_sim)

if __name__ == '__main__':
    counter=0
    company_name_list=[]
    company_number_list=[]
    company_number_sum_list=[]
    filenames = next(walk("inputs/loadprofiles/industry"), (None, None, []))[2]
    for names in filenames:
        file_name = "inputs/loadprofiles/industry/"+names+""
        file = pd.read_csv(file_name)
        counter=counter + len(list(file)) -1
        company_name_list.append(file_name)
        company_number_list.append(len(list(file)) -1)
        company_number_sum_list.append(counter)

    z=0
    lhs_field=lhsmdu.sample(6, 10)

    while z <= lhs_field.shape[1]:
        try:
            x=z-1
            z = z + 1
            #LHS Variables which forms one unique Simulation
            lhs_factor_profile= int(lhs_field[0,x]//(1/286))+1 # in range of [0 , 1]
            lhs_factor_battery= lhs_field[1,x]# in range of [0 , 1]
            lhs_factor_pv = lhs_field[2,x]# in range of [0 , 1]
            lhs_factor_control_strategy=int(lhs_field[3,x]//(1/3)) #either[0,1,]
            lhs_factor_percentage_to_peak_shave=lhs_field[4,x]
            lhs_factor_weather_region=int(lhs_field[5,x]//(1/15)+1)   #either exact [0,1,2,3...13,14]
            ###see which company
            location_list=["01Bremerhaven","02Rostock","03Hamburg","04Potsdam","05Essen",
                           "06Bad Marienburg","07Kassel","08Braunlage","09Chemnitz","10Hof",
                           "11Fichtelberg","12Mannheim","13Muehldorf","14Stoetten","15Garmisch Partenkirchen"]
            location=location_list[lhs_factor_weather_region-1]

            counter = 0
            for number in company_number_sum_list:
                if lhs_factor_profile <= number:
                    if counter == 0:
                        company_number_in_file = lhs_factor_profile
                        company_name_list_final = company_name_list[counter].replace("inputs/loadprofiles/industry/", "")
                        break
                    else:
                        company_number_in_file = lhs_factor_profile - company_number_sum_list[counter - 1]
                        company_name_list_final = company_name_list[counter].replace("inputs/loadprofiles/industry/", "")

                    break
                else:
                    counter = counter + 1

            #Get Values of Electrcity
            column_electricity_demand = pd.read_csv("inputs/loadprofiles/industry/" + company_name_list_final + "").iloc[:, [company_number_in_file]].to_numpy(dtype=float)
            max_electricity_demand=int(max(column_electricity_demand))
            sum_anual_electrcitcy_demand=int(sum(column_electricity_demand))


            # pv and battery is in every set_up
            battery_capacity = (0.01 + (12 - 0.01) * lhs_factor_battery) * sum_anual_electrcitcy_demand / (1000*1000)  # in kWh
            if int(battery_capacity) == 0:
                battery_capacity = 1

            power_pv = (0.01 + (13 - 0.01) * lhs_factor_pv) * sum_anual_electrcitcy_demand / (1000*1000)  # in kW

            # Percentage_to-Peak_shave  #Peak shaving from 0% into grid up to 70% regarding PVS
            percentage_to_peak_shave_var = lhs_factor_percentage_to_peak_shave * 0.7
            possible_control_strategies=["optimize_own_consumption", "peak_shaving_from_grid","peak_shaving_into_grid"]
            if possible_control_strategies[lhs_factor_control_strategy] == "optimize_own_consumption":
                limit_peak_shave=0
                percentage_to_peak_shave_var=0
            elif possible_control_strategies[lhs_factor_control_strategy] == "peak_shaving_from_grid":
                limit_peak_shave = int(power_pv *1000* percentage_to_peak_shave_var)

            elif possible_control_strategies[lhs_factor_control_strategy] == "peak_shaving_into_grid":
                limit_peak_shave = int(max_electricity_demand * percentage_to_peak_shave_var)


            # Create Simulation SetUp
            my_cfg = ConfigurationGenerator()

            # Set simulation parameters
            my_cfg.add_simulation_parameters()
            ####################################################################################################################
            # Set components
            # this components are always setted
            var = pd.read_csv("inputs/loadprofiles/industry/" + company_name_list_final + "")

            my_csv_loader_electricity = {"CSVLoaderEL": {"component_name": "CSVLoaderEL",
                                                 "csv_filename": os.path.join("loadprofiles/industry", str(company_name_list_final)),
                                                 "column": company_number_in_file,
                                                 "loadtype": loadtypes.LoadTypes.Electricity,
                                                 "unit": loadtypes.Units.Watt,
                                                 "column_name": str(pd.read_csv("inputs/loadprofiles/industry/" + company_name_list_final + "").columns[company_number_in_file]),
                                                 "multiplier": 1}}
            my_cfg.add_component(my_csv_loader_electricity)

            #Weather
            my_weather = {"Weather": {"location": location}}
            my_cfg.add_component(my_weather)
            #PVS
            my_pvs = {"PVSystem": {"power": int(power_pv*1000)}}
            my_cfg.add_component(my_pvs)

            my_battery = {"AdvancedBattery": {"capacity": int(battery_capacity)}}
            my_cfg.add_component(my_battery)




            my_controller = {"Controller": {"temperature_storage_target_warm_water": 35,
                                              "temperature_storage_target_heating_water": 55,
                                              "temperature_storage_target_hysteresis_ww": 30,
                                              "temperature_storage_target_hysteresis_hw": 50,
                                              "strategy": possible_control_strategies[lhs_factor_control_strategy],
                                              "limit_to_shave": limit_peak_shave,
                                              "percentage_to_shave": percentage_to_peak_shave_var}}
            my_cfg.add_component(my_controller)


            # Set connections
            my_connection_component = ComponentsConnection(first_component="Weather",
                                                           second_component="PVSystem")
            my_cfg.add_connection(my_connection_component)



            # Outputs from PVSystem
            my_pvs_to_controller = ComponentsConnection(first_component="PVSystem",
                                                        second_component="Controller",
                                                        method="Manual",
                                                        first_component_output="ElectricityOutput",
                                                        second_component_input="ElectricityOutputPvs")
            my_cfg.add_connection(my_pvs_to_controller)

            # Outputs from CSVLoader Electricity
            my_csv_to_controller_a = ComponentsConnection(first_component="CSVLoaderEL",
                                                          second_component="Controller",
                                                          method="Manual",
                                                          first_component_output="Output1",
                                                          second_component_input="ElectricityConsumptionBuilding")
            my_cfg.add_connection(my_csv_to_controller_a)


            #Outputs from Battery
            my_battery_to_controller = ComponentsConnection(first_component="Controller",
                                                     second_component="AdvancedBattery",
                                                     method="Manual",
                                                     first_component_output="ElectricityToOrFromBatteryTarget",
                                                     second_component_input="LoadingPowerInput")
            my_cfg.add_connection(my_battery_to_controller)
            #Outputs from Controller
            my_controller_to_battery = ComponentsConnection(first_component="AdvancedBattery",
                                                     second_component="Controller",
                                                     method="Manual",
                                                     first_component_output="ACBatteryPower",
                                                     second_component_input="ElectricityToOrFromBatteryReal")
            my_cfg.add_connection(my_controller_to_battery)




            # Export configuration file
            my_cfg.dump()
            os.system("python hisim.py basic_household_implicit_hyper_cube_industry basic_household_implicit_hyper_cube_industry")

        except Exception as e: print(e)





