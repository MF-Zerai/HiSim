import inspect
import numpy as np
import os

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
from SALib.sample import saltelli
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
def basic_household_implicit_salib_household(my_sim: sim.Simulator):
    my_setup_function = SetupFunction()
    my_setup_function.build(my_sim)

if __name__ == '__main__':

    problem = {
        'num_vars': 10,
        'names': ['lhs_factor_demand', 'lhs_factor_battery', 'lhs_factor_pv', 'lhs_factor_storage_h2', 'lhs_factor_setup_var',
                  'lhs_factor_heat_demand_relative_to_moderness', 'lhs_factor_which_house', 'lhs_factor_weather_region', 'lhs_factor_control_strategy', 'lhs_factor_percentage_to_peak_shave'],
        'bounds': [[0, 1],
                   [0, 1],
                   [0, 1],
                   [0, 1],
                   [0, 1],
                   [0, 1],
                   [0, 1],
                   [0, 1],
                   [0, 1],
                   [0, 1],
                   ]
    }

    param_values = saltelli.sample(problem, 4)
    z=0
    x=1
    np.savetxt("param_values_salib_household.txt", param_values)

    try:
        while z <= param_values.shape[0]:
            x=z-1
            z = z + 1
            #LHS Variables which forms one unique Simulation
            lhs_factor_demand= param_values[x,0] # in range of [0 , 1]
            lhs_factor_battery= param_values[x,1]# in range of [0 , 1]
            lhs_factor_pv = param_values[x,2]# in range of [0 , 1]
            lhs_factor_storage_h2= param_values[x,3]# in range of [0 , 1]

            lhs_factor_setup_var=int(param_values[x,4]//(1/3)) #either exact [0,1,2] 0=HP, 1=CHP+GH, 2=CHP+GH+ELCT+H2ST

            lhs_factor_heat_demand_relative_to_moderness=int(param_values[x,5]//(1/3)) #either exact [0,1,2]
            lhs_factor_which_house=int(param_values[x,6]//(1/2)) #either exact [0,1]
            lhs_factor_weather_region=int(param_values[x,7]//(1/15)+1)   #either exact [0,1,2,3...13,14]
            lhs_factor_control_strategy=int(param_values[x,8]//(1/2)) #either[0,1,2]
            lhs_factor_percentage_to_peak_shave=param_values[x,9]
            location_list=["01Bremerhaven","02Rostock","03Hamburg","04Potsdam","05Essen",
                           "06Bad Marienburg","07Kassel","08Braunlage","09Chemnitz","10Hof",
                           "11Fichtelberg","12Mannheim","13Muehldorf","14Stoetten","15Garmisch Partenkirchen"]
            location=location_list[lhs_factor_weather_region-1]
            #Choose house and calculate specific HeatWater/WarmWater/Electricity demand
            factor_which_house=["sfh" , "mfh"]
            if factor_which_house[lhs_factor_which_house] == "sfh":
                factor_electricity=2000 + (8000-2000)*lhs_factor_demand #in kWh yearly
                factor_warm_water=500 + (3000-500)*lhs_factor_demand #in kWh yearly
                heat_demand_relative_to_moderness=[25,75,200]
                #implement random number in between one and three

                factor_heating_water= 150 * heat_demand_relative_to_moderness[lhs_factor_heat_demand_relative_to_moderness] # all in kWh
            elif factor_which_house[lhs_factor_which_house] == "mfh":
                factor_electricity=9000 + (75000-9000)*lhs_factor_demand #in kWh yearly
                factor_warm_water=3000+ (25000-3000)*lhs_factor_demand #in kWh yearly
                size_building=(2+(25-2)*lhs_factor_demand)*70 # in m^2
                factor_heating_water= size_building * 50  #50kWh/m^2, all in kWh


            #pv and battery is in every set_up
            battery_capacity= (0.01 + (8-0.01)*lhs_factor_battery)*factor_electricity/1000 #in kWh
            if int(battery_capacity)==0:
                battery_capacity=1

            power_pv=(0.01+(8-0.01)*lhs_factor_pv)*factor_electricity/1000#in kW
            lhs_factor_percentage_to_peak_shave
            #Percentage_to-Peak_shave
  #Peak shaving from 0% into grid up to 70% regarding PVS
            percentage_to_peak_shave_var= lhs_factor_percentage_to_peak_shave*0.7
            limit_peak_shave=int(power_pv *1000* percentage_to_peak_shave_var)

            ###Define additional Setup of House
            file_name="inputs/loadprofiles/vdi-4655/vdi-4655_mfh-existing_try-1_15min.csv"

            #Calculate Energy Components of house based on specific Demand
            file_name="inputs/loadprofiles/vdi-4655/vdi-4655_"+str(factor_which_house[lhs_factor_which_house])+"-existing_try-"+str(lhs_factor_weather_region)+"_15min.csv"
            file = pd.read_csv(file_name)
            column_space_heating_demand = file.iloc[:, [2]].to_numpy(dtype=float)
            column_domestic_water_demand = file.iloc[:, [3]].to_numpy(dtype=float)

            # Find day with highest heat demand to set up Heating Components
            column_sum_heating = column_space_heating_demand
            x = 1
            highest_heat_demand = 0
            while x <= 365:
                new_day_highest_heat_demand = np.mean(column_sum_heating[(96 * (x - 1)):(96 * x)])
                if new_day_highest_heat_demand > highest_heat_demand:
                    highest_heat_demand = new_day_highest_heat_demand
                    highest_warm_water_demand= np.mean(column_domestic_water_demand[(96 * (x - 1)):(96 * x)])
                x = x + 1

            # Calculate Average Heating demand of the day
            power_hp = 1.5* (highest_heat_demand*factor_heating_water+highest_warm_water_demand*factor_warm_water)/1000  # in W
            power_gh = 1.5* (highest_heat_demand*factor_heating_water+highest_warm_water_demand*factor_warm_water)/1000  # in w

            if factor_which_house[lhs_factor_which_house] == "sfh":
                power_chp=factor_heating_water/1000*0.15*(np.mean(column_sum_heating))*8.76/1000 #[kWel]
                power_elekt=power_chp*2


            elif factor_which_house[lhs_factor_which_house] == "mfh":
                power_chp =factor_heating_water/1000*0.1*(np.mean(column_sum_heating))*8.76/1000   # [kWel]
                power_elekt=power_chp*2
            if power_elekt<1.4:
                power_elekt=1.4
            #setup_storage_size
            storage_size_ww=0.2*factor_warm_water #in litres

            if lhs_factor_setup_var==0:
                storage_size_hw=100 * (power_hp)/1000#55litre per each kW power heaters
            else:
                storage_size_hw = 100 * (power_chp*1000+power_gh)/1000 #55litre per each kW power heaters

            my_hydrogen_storage_size= 200*power_elekt/2.4 + 2000*power_elekt/2.4* lhs_factor_storage_h2
            if my_hydrogen_storage_size < 1:
                my_hydrogen_storage_size=1

            ####Schranke einbauen mit 3kw
            # Create Simulation SetUp
            my_cfg = ConfigurationGenerator()

            # Set simulation parameters
            my_cfg.add_simulation_parameters()
            ####################################################################################################################
            # Set components
            # this components are always setted
            my_csv_loader_warm_water = {"CSVLoaderWW": {"component_name": "CSVLoaderWW",
                                                 "csv_filename": os.path.join("loadprofiles/vdi-4655", "vdi-4655_"+str(factor_which_house[lhs_factor_which_house])+"-existing_try-"+str(lhs_factor_weather_region)+"_15min.csv"),
                                                 "column": 3,
                                                 "loadtype": loadtypes.LoadTypes.Heating,
                                                 "unit": loadtypes.Units.Watt,
                                                 "column_name": "domestic water demand [W]",
                                                 "multiplier": int(factor_warm_water)/1000}}
            my_cfg.add_component(my_csv_loader_warm_water)

            my_csv_loader_heating_water = {"CSVLoaderHW": {"component_name": "CSVLoaderHW",
                                                 "csv_filename": os.path.join("loadprofiles/vdi-4655", "vdi-4655_"+str(factor_which_house[lhs_factor_which_house])+"-existing_try-"+str(lhs_factor_weather_region)+"_15min.csv"),
                                                 "column": 2,
                                                 "loadtype": loadtypes.LoadTypes.Heating,
                                                 "unit": loadtypes.Units.Watt,
                                                 "column_name": "space heating demand [W]",
                                                 "multiplier": int(factor_heating_water)/1000}}
            my_cfg.add_component(my_csv_loader_heating_water)

            my_csv_loader_electricity = {"CSVLoaderEL": {"component_name": "CSVLoaderEL",
                                                 "csv_filename": os.path.join("loadprofiles/vdi-4655", "vdi-4655_"+str(factor_which_house[lhs_factor_which_house])+"-existing_try-"+str(lhs_factor_weather_region)+"_15min.csv"),
                                                 "column": 1,
                                                 "loadtype": loadtypes.LoadTypes.Electricity,
                                                 "unit": loadtypes.Units.Watt,
                                                 "column_name": "electricity demand, house [W]",
                                                 "multiplier": int(factor_electricity)/1000}}
            my_cfg.add_component(my_csv_loader_electricity)


            #Weather
            my_weather = {"Weather": {"location": location}}
            my_cfg.add_component(my_weather)

            #PVS
            my_pvs = {"PVSystem": {"power": int(power_pv*1000)}}
            my_cfg.add_component(my_pvs)

            my_battery = {"AdvancedBattery": {"capacity": int(battery_capacity)}}
            my_cfg.add_component(my_battery)

            #Storages Water
            my_heat_storage = {"HeatStorage": {"V_SP_heating_water": int(storage_size_hw),
                                              "V_SP_warm_water": int(storage_size_ww),
                                              "temperature_of_warm_water_extratcion": 35,
                                              "ambient_temperature": 15}}
            my_cfg.add_component(my_heat_storage)


            possible_control_strategies=["optimize_own_consumption", "peak_shaving_into_grid","seasonal_storage"]
            if possible_control_strategies[lhs_factor_control_strategy] == "optimize_own_consumption" or lhs_factor_setup_var == 2:
                limit_peak_shave=0
                percentage_to_peak_shave_var=0
                if possible_control_strategies[lhs_factor_control_strategy] == "seasonal_storage":
                    lhs_factor_setup_var=1
            if lhs_factor_setup_var==0: #HP
                my_controller = {"Controller": {"temperature_storage_target_warm_water": 35,
                                                  "temperature_storage_target_heating_water": 55,
                                                  "temperature_storage_target_hysteresis_ww": 30,
                                                  "temperature_storage_target_hysteresis_hw": 50,
                                                  "strategy": possible_control_strategies[lhs_factor_control_strategy],
                                                  "limit_to_shave": limit_peak_shave,
                                                  "percentage_to_shave": percentage_to_peak_shave_var}}
                my_cfg.add_component(my_controller)

                #heat pump
                hp_manufacturer = "Generic"
                hp_type = 1  # air/water | regulated
                hp_thermal_power = int(power_hp)  # W
                hp_t_input = -7  # °C
                hp_t_output = 52  # °C
                my_heat_pump_hplib = {"HeatPumpHplib": {"model": "Generic",
                                                        "group_id": hp_type,
                                                        "t_in": hp_t_input,
                                                        "t_out": hp_t_output,
                                                        "p_th_set": hp_thermal_power}}
                my_cfg.add_component(my_heat_pump_hplib)

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

                my_csv_to_controller_b = ComponentsConnection(first_component="CSVLoaderWW",
                                                              second_component="HeatStorage",
                                                              method="Manual",
                                                              first_component_output="Output1",
                                                              second_component_input="ThermalDemandWarmWater")
                my_cfg.add_connection(my_csv_to_controller_b)

                my_csv_to_controller_c = ComponentsConnection(first_component="CSVLoaderHW",
                                                              second_component="HeatStorage",
                                                              method="Manual",
                                                              first_component_output="Output1",
                                                              second_component_input="ThermalDemandHeatingWater")
                my_cfg.add_connection(my_csv_to_controller_c)

                # Outputs from Weather
                my_weather_to_heat_pump_a = ComponentsConnection(first_component="Weather",
                                                                 second_component="HeatPumpHplib",
                                                                 method="Manual",
                                                                 first_component_output="TemperatureOutside",
                                                                 second_component_input="TemperatureInputPrimary")
                my_cfg.add_connection(my_weather_to_heat_pump_a)

                my_weather_to_heat_pump_b = ComponentsConnection(first_component="Weather",
                                                                 second_component="HeatPumpHplib",
                                                                 method="Manual",
                                                                 first_component_output="TemperatureOutside",
                                                                 second_component_input="TemperatureAmbient")
                my_cfg.add_connection(my_weather_to_heat_pump_b)

                # Outputs from Storage
                my_storage_to_controller_a = ComponentsConnection(first_component="HeatStorage",
                                                                  second_component="Controller",
                                                                  method="Manual",
                                                                  first_component_output="WaterOutputTemperatureHeatingWater",
                                                                  second_component_input="StorageTemperatureHeatingWater")
                my_cfg.add_connection(my_storage_to_controller_a)

                my_storage_to_controller_b = ComponentsConnection(first_component="HeatStorage",
                                                                  second_component="Controller",
                                                                  method="Manual",
                                                                  first_component_output="WaterOutputTemperatureWarmWater",
                                                                  second_component_input="StorageTemperatureWarmWater")
                my_cfg.add_connection(my_storage_to_controller_b)

                my_storage_to_heat_pump = ComponentsConnection(first_component="HeatStorage",
                                                               second_component="HeatPumpHplib",
                                                               method="Manual",
                                                               first_component_output="WaterOutputStorageforHeaters",
                                                               second_component_input="TemperatureInputSecondary")
                my_cfg.add_connection(my_storage_to_heat_pump)

                # Outputs from HeatPump
                my_heat_pump_to_heat_storage = ComponentsConnection(first_component="HeatPumpHplib",
                                                                    second_component="HeatStorage",
                                                                    method="Manual",
                                                                    first_component_output="ThermalOutputPower",
                                                                    second_component_input="ThermalInputPower3")
                my_cfg.add_connection(my_heat_pump_to_heat_storage)

                my_heat_pump_to_controller = ComponentsConnection(first_component="HeatPumpHplib",
                                                                  second_component="Controller",
                                                                  method="Manual",
                                                                  first_component_output="ElectricalInputPower",
                                                                  second_component_input="ElectricityDemandHeatPump")
                my_cfg.add_connection(my_heat_pump_to_controller)

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

                my_controller_to_heat_pump = ComponentsConnection(first_component="Controller",
                                                                  second_component="HeatPumpHplib",
                                                                  method="Manual",
                                                                  first_component_output="ControlSignalHeatPump",
                                                                  second_component_input="Mode")
                my_cfg.add_connection(my_controller_to_heat_pump)

                my_controller_to_heat_storage = ComponentsConnection(first_component="Controller",
                                                                     second_component="HeatStorage",
                                                                     method="Manual",
                                                                     first_component_output="ControlSignalChooseStorage",
                                                                     second_component_input="ControlSignalChooseStorage")
                my_cfg.add_connection(my_controller_to_heat_storage)

            elif lhs_factor_setup_var==1: #CHP+GH
                my_controller = {"Controller": {"temperature_storage_target_warm_water": 35,
                                                  "temperature_storage_target_heating_water": 55,
                                                  "temperature_storage_target_hysteresis_ww": 30,
                                                  "temperature_storage_target_hysteresis_hw": 50,
                                                  "strategy": possible_control_strategies[lhs_factor_control_strategy],
                                                  "limit_to_shave": limit_peak_shave,
                                                  "percentage_to_shave": percentage_to_peak_shave_var}}
                my_cfg.add_component(my_controller)

                # CHP
                my_chp = {"CHP": {"min_operation_time": 60,
                                  "min_idle_time": 15,
                                  "gas_type": "Methan",
                                  "operating_mode": "heat",
                                  "p_el_max": int(power_chp*1000)}}
                my_cfg.add_component(my_chp)

                # GasHeater
                my_gas_heater = {"GasHeater": {"temperaturedelta": 15,
                                 "power_max": int(power_gh)}}
                my_cfg.add_component(my_gas_heater)

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

                my_csv_to_controller_b = ComponentsConnection(first_component="CSVLoaderWW",
                                                              second_component="HeatStorage",
                                                              method="Manual",
                                                              first_component_output="Output1",
                                                              second_component_input="ThermalDemandWarmWater")
                my_cfg.add_connection(my_csv_to_controller_b)

                my_csv_to_controller_c = ComponentsConnection(first_component="CSVLoaderHW",
                                                              second_component="HeatStorage",
                                                              method="Manual",
                                                              first_component_output="Output1",
                                                              second_component_input="ThermalDemandHeatingWater")
                my_cfg.add_connection(my_csv_to_controller_c)

                # Outputs from Battery
                my_battery_to_controller = ComponentsConnection(first_component="Controller",
                                                                second_component="AdvancedBattery",
                                                                method="Manual",
                                                                first_component_output="ElectricityToOrFromBatteryTarget",
                                                                second_component_input="LoadingPowerInput")
                my_cfg.add_connection(my_battery_to_controller)

                # Outputs from Storage
                my_storage_to_controller_a = ComponentsConnection(first_component="HeatStorage",
                                                                  second_component="Controller",
                                                                  method="Manual",
                                                                  first_component_output="WaterOutputTemperatureHeatingWater",
                                                                  second_component_input="StorageTemperatureHeatingWater")
                my_cfg.add_connection(my_storage_to_controller_a)

                my_storage_to_controller_b = ComponentsConnection(first_component="HeatStorage",
                                                                  second_component="Controller",
                                                                  method="Manual",
                                                                  first_component_output="WaterOutputTemperatureWarmWater",
                                                                  second_component_input="StorageTemperatureWarmWater")
                my_cfg.add_connection(my_storage_to_controller_b)

                my_storage_to_gas_heater = ComponentsConnection(first_component="HeatStorage",
                                                                second_component="GasHeater",
                                                                method="Manual",
                                                                first_component_output="WaterOutputStorageforHeaters",
                                                                second_component_input="MassflowInputTemperature")
                my_cfg.add_connection(my_storage_to_gas_heater)

                my_storage_to_chp = ComponentsConnection(first_component="HeatStorage",
                                                         second_component="CHP",
                                                         method="Manual",
                                                         first_component_output="WaterOutputStorageforHeaters",
                                                         second_component_input="MassflowInputTemperature")
                my_cfg.add_connection(my_storage_to_chp)

                # Outputs from CHP

                my_chp_to_controller_a = ComponentsConnection(first_component="CHP",
                                                              second_component="Controller",
                                                              method="Manual",
                                                              first_component_output="ElectricityOutput",
                                                              second_component_input="ElectricityFromCHPReal")
                my_cfg.add_connection(my_chp_to_controller_a)
                my_chp_to_heat_storage = ComponentsConnection(first_component="CHP",
                                                              second_component="HeatStorage",
                                                              method="Manual",
                                                              first_component_output="ThermalOutputPower",
                                                              second_component_input="ThermalInputPower1")
                my_cfg.add_connection(my_chp_to_heat_storage)

                # Outputs from GasHeater

                my_gas_heater_to_heat_storage = ComponentsConnection(first_component="GasHeater",
                                                                     second_component="HeatStorage",
                                                                     method="Manual",
                                                                     first_component_output="ThermalOutputPower",
                                                                     second_component_input="ThermalInputPower2")
                my_cfg.add_connection(my_gas_heater_to_heat_storage)

                # Outputs from Controller
                my_controller_to_battery = ComponentsConnection(first_component="AdvancedBattery",
                                                                second_component="Controller",
                                                                method="Manual",
                                                                first_component_output="ACBatteryPower",
                                                                second_component_input="ElectricityToOrFromBatteryReal")
                my_cfg.add_connection(my_controller_to_battery)

                my_controller_to_chp_a = ComponentsConnection(first_component="Controller",
                                                              second_component="CHP",
                                                              method="Manual",
                                                              first_component_output="ElectricityFromCHPTarget",
                                                              second_component_input="ElectricityFromCHPTarget")
                my_cfg.add_connection(my_controller_to_chp_a)

                my_controller_to_chp_b = ComponentsConnection(first_component="Controller",
                                                              second_component="CHP",
                                                              method="Manual",
                                                              first_component_output="ControlSignalChp",
                                                              second_component_input="ControlSignal")
                my_cfg.add_connection(my_controller_to_chp_b)

                my_controller_to_gas_heater = ComponentsConnection(first_component="Controller",
                                                                   second_component="GasHeater",
                                                                   method="Manual",
                                                                   first_component_output="ControlSignalGasHeater",
                                                                   second_component_input="ControlSignal")
                my_cfg.add_connection(my_controller_to_gas_heater)

                my_controller_to_heat_storage = ComponentsConnection(first_component="Controller",
                                                                     second_component="HeatStorage",
                                                                     method="Manual",
                                                                     first_component_output="ControlSignalChooseStorage",
                                                                     second_component_input="ControlSignalChooseStorage")
                my_cfg.add_connection(my_controller_to_heat_storage)




            elif lhs_factor_setup_var==2: #CHP+GH+ELEKT+H2ST
                lhs_factor_control_strategy==2 #Control strategy seasonal Storage bec of setup
                my_controller = {"Controller": {"temperature_storage_target_warm_water": 35,
                                                  "temperature_storage_target_heating_water": 55,
                                                  "temperature_storage_target_hysteresis_ww": 30,
                                                  "temperature_storage_target_hysteresis_hw": 50,
                                                  "strategy": "seasonal_storage",
                                                  "percentage_to_shave": percentage_to_peak_shave_var}}
                my_cfg.add_component(my_controller)

                #CHP
                my_chp = {"CHP": {"min_operation_time": 60,
                                  "min_idle_time": 15,
                                  "gas_type": "Hydrogen",
                                  "operating_mode": "electricity",
                                  "p_el_max": int(power_chp*1000)}}
                my_cfg.add_component(my_chp)

                # GasHeater
                my_gas_heater = {"GasHeater": {"temperaturedelta": 15,
                                               "power_max": int(power_gh)}}
                my_cfg.add_component(my_gas_heater)

                my_hydrogen_storage = {"HydrogenStorage": {"component_name": "HydrogenStorage",
                                                           "max_capacity": int(my_hydrogen_storage_size)}}
                my_cfg.add_component(my_hydrogen_storage)
                #Electrolyzer
                my_electrolyzer = {"Electrolyzer": {"component_name": "Electrolyzer",
                                                    "power_electrolyzer": int(power_elekt*1000)}}
                my_cfg.add_component(my_electrolyzer)

                #Hydrogen Storage


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

                my_csv_to_controller_b = ComponentsConnection(first_component="CSVLoaderWW",
                                                              second_component="HeatStorage",
                                                              method="Manual",
                                                              first_component_output="Output1",
                                                              second_component_input="ThermalDemandWarmWater")
                my_cfg.add_connection(my_csv_to_controller_b)

                my_csv_to_controller_c = ComponentsConnection(first_component="CSVLoaderHW",
                                                              second_component="HeatStorage",
                                                              method="Manual",
                                                              first_component_output="Output1",
                                                              second_component_input="ThermalDemandHeatingWater")
                my_cfg.add_connection(my_csv_to_controller_c)

                # Outputs from Storage
                my_storage_to_controller_a = ComponentsConnection(first_component="HeatStorage",
                                                                  second_component="Controller",
                                                                  method="Manual",
                                                                  first_component_output="WaterOutputTemperatureHeatingWater",
                                                                  second_component_input="StorageTemperatureHeatingWater")
                my_cfg.add_connection(my_storage_to_controller_a)

                my_storage_to_controller_b = ComponentsConnection(first_component="HeatStorage",
                                                                  second_component="Controller",
                                                                  method="Manual",
                                                                  first_component_output="WaterOutputTemperatureWarmWater",
                                                                  second_component_input="StorageTemperatureWarmWater")
                my_cfg.add_connection(my_storage_to_controller_b)

                my_storage_to_gas_heater = ComponentsConnection(first_component="HeatStorage",
                                                                second_component="GasHeater",
                                                                method="Manual",
                                                                first_component_output="WaterOutputStorageforHeaters",
                                                                second_component_input="MassflowInputTemperature")
                my_cfg.add_connection(my_storage_to_gas_heater)

                my_storage_to_chp = ComponentsConnection(first_component="HeatStorage",
                                                         second_component="CHP",
                                                         method="Manual",
                                                         first_component_output="WaterOutputStorageforHeaters",
                                                         second_component_input="MassflowInputTemperature")
                my_cfg.add_connection(my_storage_to_chp)

                # Outputs from Battery
                my_battery_to_controller = ComponentsConnection(first_component="Controller",
                                                                second_component="AdvancedBattery",
                                                                method="Manual",
                                                                first_component_output="ElectricityToOrFromBatteryTarget",
                                                                second_component_input="LoadingPowerInput")
                my_cfg.add_connection(my_battery_to_controller)

                # Outputs from CHP

                my_chp_to_controller_a = ComponentsConnection(first_component="CHP",
                                                              second_component="Controller",
                                                              method="Manual",
                                                              first_component_output="ElectricityOutput",
                                                              second_component_input="ElectricityFromCHPReal")
                my_cfg.add_connection(my_chp_to_controller_a)
                my_chp_to_heat_storage = ComponentsConnection(first_component="CHP",
                                                              second_component="HeatStorage",
                                                              method="Manual",
                                                              first_component_output="ThermalOutputPower",
                                                              second_component_input="ThermalInputPower1")
                my_cfg.add_connection(my_chp_to_heat_storage)

                my_chp_to_hydrogen_storage = ComponentsConnection(first_component="CHP",
                                                              second_component="HydrogenStorage",
                                                              method="Manual",
                                                              first_component_output="GasDemandTarget",
                                                              second_component_input="DischargingHydrogenAmountTarget")
                my_cfg.add_connection(my_chp_to_hydrogen_storage)



                # Outputs from Electrolyzer and Hydrogen Storage
                my_hydrogen_storage_to_chp = ComponentsConnection(first_component="HydrogenStorage",
                                                              second_component="CHP",
                                                              method="Manual",
                                                              first_component_output="HydrogenNotReleased",
                                                              second_component_input="HydrogenNotReleased")
                my_cfg.add_connection(my_hydrogen_storage_to_chp)

                my_electrolyzer_to_hydrogen_storage = ComponentsConnection(first_component="Electrolyzer",
                                                              second_component="HydrogenStorage",
                                                              method="Manual",
                                                              first_component_output="HydrogenOutput",
                                                              second_component_input="ChargingHydrogenAmount")
                my_cfg.add_connection(my_electrolyzer_to_hydrogen_storage)

                my_hydrogen_storage_to_electrolyzer= ComponentsConnection(first_component="HydrogenStorage",
                                                              second_component="Electrolyzer",
                                                              method="Manual",
                                                              first_component_output="HydrogenNotStored",
                                                              second_component_input="HydrogenNotStored")
                my_cfg.add_connection(my_hydrogen_storage_to_electrolyzer)

                my_electrolyzer_to_controller_a = ComponentsConnection(first_component="Electrolyzer",
                                                              second_component="Controller",
                                                              method="Manual",
                                                              first_component_output="UnusedPower",
                                                              second_component_input="ElectricityToElectrolyzerUnused")
                my_cfg.add_connection(my_electrolyzer_to_controller_a)
                my_controller_to_electrolyzer= ComponentsConnection(first_component="Controller",
                                                              second_component="Electrolyzer",
                                                              method="Manual",
                                                              first_component_output="ElectricityToElectrolyzerTarget",
                                                              second_component_input="ElectricityInput")
                my_cfg.add_connection(my_controller_to_electrolyzer)


                # Outputs from GasHeater

                my_gas_heater_to_heat_storage = ComponentsConnection(first_component="GasHeater",
                                                                     second_component="HeatStorage",
                                                                     method="Manual",
                                                                     first_component_output="ThermalOutputPower",
                                                                     second_component_input="ThermalInputPower2")
                my_cfg.add_connection(my_gas_heater_to_heat_storage)

                # Outputs from Controller
                my_controller_to_battery = ComponentsConnection(first_component="AdvancedBattery",
                                                                second_component="Controller",
                                                                method="Manual",
                                                                first_component_output="ACBatteryPower",
                                                                second_component_input="ElectricityToOrFromBatteryReal")
                my_cfg.add_connection(my_controller_to_battery)

                my_controller_to_chp_a = ComponentsConnection(first_component="Controller",
                                                              second_component="CHP",
                                                              method="Manual",
                                                              first_component_output="ElectricityFromCHPTarget",
                                                              second_component_input="ElectricityFromCHPTarget")
                my_cfg.add_connection(my_controller_to_chp_a)

                my_controller_to_chp_b = ComponentsConnection(first_component="Controller",
                                                              second_component="CHP",
                                                              method="Manual",
                                                              first_component_output="ControlSignalChp",
                                                              second_component_input="ControlSignal")
                my_cfg.add_connection(my_controller_to_chp_b)

                my_controller_to_gas_heater = ComponentsConnection(first_component="Controller",
                                                                   second_component="GasHeater",
                                                                   method="Manual",
                                                                   first_component_output="ControlSignalGasHeater",
                                                                   second_component_input="ControlSignal")
                my_cfg.add_connection(my_controller_to_gas_heater)

                my_controller_to_heat_storage = ComponentsConnection(first_component="Controller",
                                                                     second_component="HeatStorage",
                                                                     method="Manual",
                                                                     first_component_output="ControlSignalChooseStorage",
                                                                     second_component_input="ControlSignalChooseStorage")
                my_cfg.add_connection(my_controller_to_heat_storage)



            # Export configuration file
            my_cfg.dump()
            os.system("python hisim.py basic_household_implicit_hyper_cube basic_household_implicit_hyper_cube")


    except OSError:
        print("Error")



