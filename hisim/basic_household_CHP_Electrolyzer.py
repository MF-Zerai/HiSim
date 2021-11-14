import os
import sys
import globals
import numpy as np
import simulator as sim
import loadtypes
import start_simulation
import components as cps
from components import occupancy
from components import weather
from components import building
from components import heat_pump_hplib
from components import controller
from components import storage
from components import pvs
from components import advanced_battery
from components import configuration
from components import chp_system
from components.hydrogen_generator import Electrolyzer ,HydrogenStorage
from components.demand_el import DemandEl
from components.configuration import HydrogenStorageConfig, ElectrolyzerConfig


__authors__ = "Max Hillen, Tjarko Tjaden"
__copyright__ = "Copyright 2021, the House Infrastructure Project"
__credits__ = ["Noah Pflugradt"]
__license__ = "MIT"
__version__ = "0.1"
__maintainer__ = "Max Hillen"
__email__ = "max.hillen@fz-juelich.de"
__status__ = "development"
#power=E3 10E3 25E3 100E3
power = 1000E3
#capacitiy=  25 100
capacitiy=100
def basic_household(my_sim,capacity=capacitiy,power=power):
    """
    This setup function represents an household including
    electric and thermal consumption and a heatpump.

    - Simulation Parameters
    - Components
        - Weather
        - Building
        - Occupancy (Residents' Demands)
        - Heat Pump
    """

    ##### System Parameters #####

    # Set simulation parameters
    year = 2021
    seconds_per_timestep = 60*15

    # Set weather
    location = "Aachen"

    # Set occupancy
    occupancy_profile = "CH01"

    # Set building
    building_code = "DE.N.SFH.05.Gen.ReEx.001.002"
    building_class = "medium"
    initial_temperature = 23

    # Set photovoltaic system
    time = 2019

    load_module_data = False
    module_name = "Hanwha_HSL60P6_PA_4_250T__2013_"
    integrateInverter = True
    inverter_name = "ABB__MICRO_0_25_I_OUTD_US_208_208V__CEC_2014_"
    # Set Battery

    #Set CHP
    min_operation_time = 60
    min_idle_time = 15
    gas_type = "Hydrogen"
    #Set Electrolyzer
    electrolyzer_c = ElectrolyzerConfig()

    #Set Hydrogen Storage
    hydrogen_storage_c=HydrogenStorageConfig()

    # Set heat pump
    hp_manufacturer = "Generic"
    hp_type = 1 # air/water | regulated
    hp_thermal_power = 12000 # W
    hp_t_input = -7 # °C
    hp_t_output = 52 # °C

    # Set warm water storage
    wws_volume = 500 # l
    wws_temp_outlet=35
    wws_temp_ambient=15

    ##### Build Components #####

    # Build system parameters
    my_sim_params: sim.SimulationParameters = sim.SimulationParameters.full_year(year=year,
                                                                                 seconds_per_timestep=seconds_per_timestep)
    my_sim.set_parameters(my_sim_params)

    #ElectricityDemand
    csv_load_power_demand = DemandEl(component_name="csv_load_power_demand",
                                      csv_filename="loadprofiles/vdi-4655_mfh-existing_try-1_15min.csv",
                                      column=1,
                                      loadtype=loadtypes.LoadTypes.Electricity,
                                      unit=loadtypes.Units.Watt,
                                      column_name='"electricity demand, house [W]"',
                                      multiplier=6)
    my_sim.add_component(csv_load_power_demand)

    # Build occupancy
    #my_occupancy = occupancy.Occupancy(profile=occupancy_profile)
    #my_sim.add_component(my_occupancy)

    # Build Weather
    my_weather = weather.Weather(location=location)
    my_sim.add_component(my_weather)

    # Build CHP





    #Build Controller
    my_controller = controller.Controller(strategy="seasonal_storage")



    my_controller.connect_input(my_controller.ElectricityConsumptionBuilding,
                               csv_load_power_demand.ComponentName,
                               csv_load_power_demand.Output1)






    #my_sim.add_component(my_battery)

    my_sim.add_component(my_controller)






def basic_household_implicit(my_sim):
    pass

