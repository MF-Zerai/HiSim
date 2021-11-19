import globals
import numpy as np
import pandas as pd
import json
import os
import pickle
import seaborn as sns

#plot stuff
import matplotlib.pyplot as plt
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm
from matplotlib.ticker import MaxNLocator

class PostProcessor:
    def __init__(self,
                 folder_name : str, #folder has to be in results
                 json_file_name : str,
                 pickle_file_name:str,
                 start_date : str, #in
                 end_date : str,
                 heat_map_precision_factor: int,
                 plot_heat_map=True,
                 plot_all_houses=True,
                 plot_efh=False,
                 plot_mfh=False,
                 plot_strategy_all=True,
                 plot_strategy_own_consumption=True,
                 plot_strategy_seasonal_storage=True,
                 plot_strategy_peak_shave_into_grid =True,
                 plot_self_consumption=True,
                 plot_autarky=True,
                 plot_battery_and_pv=True,
                 plot_h2_storage=True):
        self.folder_name=folder_name
        self.start_date = start_date
        self.end_date = end_date
        self.json_file_name = json_file_name
        self.pickle_file_name = pickle_file_name
        self.heat_map_precision_factor = heat_map_precision_factor

        self.flags_performance_indicators ={"plot_self_consumption": plot_self_consumption,
                                            "plot_autarky": plot_autarky}
        self.flags_plots ={"plot_heat_map": plot_heat_map}
        self.flags_houses = {"plot_all_houses": plot_all_houses,
                              "plot_sfh": plot_efh,
                              "plot_mfh": plot_mfh}
        self.flags_strategy= {"plot_strategy_all": plot_strategy_all,
                              "plot_strategy_own_consumption": plot_strategy_own_consumption,
                              "plot_strategy_seasonal_storage": plot_strategy_seasonal_storage,
                              "plot_strategy_peak_shave_into_grid": plot_strategy_peak_shave_into_grid}
        self.flags_components={"plot_battery_and_pv": plot_battery_and_pv,
                              "plot_h2_storage": plot_h2_storage}
    def get_json_data(self,new_list,target_matrix):

        for a in  range(len(new_list)):
            newrow = []
            #soemtimes cfg isn't saved. idk why
            try :
                json.load(open(os.path.join(globals.HISIMPATH["results"], ""+str(new_list[a])+"/"+str(self.json_file_name)+".json")))
            except OSError:
                print("Error:not found: "+(os.path.join(globals.HISIMPATH["results"], ""+str(new_list[a])+"/"+str(self.json_file_name)+".json"))+"")
                continue
            json_data=json.load(open(os.path.join(globals.HISIMPATH["results"], ""+str(new_list[a])+"/"+str(self.json_file_name)+".json")))#
            newrow.append(json_data.get("Components", {}).get("Weather", {}).get("location", None ))
            housetype=(json_data.get("Components", {}).get("CSVLoaderWW", {}).get("csv_filename", None ))
            if "mfh" in housetype:
                newrow.append("mfh")
            elif "sfh" in housetype:
                newrow.append("sfh")
            else:
                print("Error: not efh or mfh is the housetype")
            newrow.append(json_data.get("Components", {}).get("CSVLoaderWW", {}).get("multiplier", None ))
            newrow.append(json_data.get("Components", {}).get("CSVLoaderHW", {}).get("multiplier", None ))
            newrow.append(json_data.get("Components", {}).get("CSVLoaderEL", {}).get("multiplier", None ))
            newrow.append(json_data.get("Components", {}).get("PVSystem", {}).get("power", None ))
            newrow.append(json_data.get("Components", {}).get("AdvancedBattery", {}).get("capacity", None ))
            newrow.append(json_data.get("Components", {}).get("HeatPumpHplib", {}).get("p_th_set", None ))
            newrow.append(json_data.get("Components", {}).get("GasHeater", {}).get("power_max", None ))
            newrow.append(json_data.get("Components", {}).get("CHP", {}).get("p_el_max", None ))
            newrow.append(json_data.get("Components", {}).get("Electrolyzer", {}).get("power_electrolyzer", None ))
            newrow.append(json_data.get("Components", {}).get("HeatStorage", {}).get("V_SP_heating_water", None ))
            newrow.append(json_data.get("Components", {}).get("HeatStorage", {}).get("V_SP_warm_water", None ))
            newrow.append(json_data.get("Components", {}).get("HydrogenStorage", {}).get("max_capacity", None ))
            newrow.append(json_data.get("Components", {}).get("Controller", {}).get("strategy", None ))
            newrow.append(json_data.get("Components", {}).get("Controller", {}).get("percentage_to_shave", None ))
            target_matrix = np.vstack([target_matrix, newrow])
        return target_matrix


    def get_all_relevant_folders(self):
        folder_list=os.listdir(os.path.join(globals.HISIMPATH["results"]))
        new_list=[]
        start_date = int(self.start_date.replace("_", ""))
        end_date = int(self.end_date.replace("_", ""))
        a=0
        while a < len(folder_list):
            a=a+1
            if self.folder_name in folder_list[a-1]:
                variable=int(folder_list[a-1].replace(self.folder_name,"").replace("_",""))
                if start_date <= variable and variable<=end_date:
                    new_list.append(folder_list[a-1])
        return new_list

    def get_pickle_informations(self,new_list,key_performance_indicators,target_matrix):
        for a in  range(len(new_list)):
            newrow = []
            objects=[]
            #soemtimes pickle isn't saved. idk why
            try:
                with open((os.path.join(globals.HISIMPATH["results"],
                                        "" + str(new_list[a]) + "/" + str(self.pickle_file_name) + ".pkl")),
                          "rb") as openfile:
                    try:
                        objects.append(pickle.load(openfile))
                    except OSError:
                        print(self.pickle_file_name)
                    #Here starts Calculation of Parameters
                    A = (objects[0]['results'].T.T)
                    sum_Produced_Elect_pv= sum((A["PVSystem - ElectricityOutput [Electricity - W]"]))
                    sum_Demand_Elect_house = sum((A["CSVLoaderEL - electricity demand, house [W] [Electricity - W]"]))


                    sum_Electricity_From_Grid=sum(x for x in A["Controller - ElectricityToOrFromGrid [Electricity - W]"] if x > 0)
                    #weird thing, which only happens if Electrolyzer is in system. Than out of some reason electricity goes into grid, when it shouldnt.
                    #but rest of the values or right
                    sum_Electricity_Into_Grid=0
                    sum_Electricity_From_Grid=0
                    variable_to_watch_weird_elect_thing=0
                    for x, y in zip(A["Controller - ElectricityToOrFromGrid [Electricity - W]"],A["Controller - ElectricityToOrFromBatteryTarget [Electricity - W]"]):
                        if x<0 and y<0:
                            sum_Electricity_From_Grid=sum_Electricity_From_Grid-y
                            variable_to_watch_weird_elect_thing=1
                            continue
                        elif x>0:
                            sum_Electricity_From_Grid=sum_Electricity_From_Grid+x
                        elif x<0:
                            sum_Electricity_Into_Grid=sum_Electricity_Into_Grid-x
                    if variable_to_watch_weird_elect_thing==1:
                        if "Electrolyzer - Unused Power [Electricity - W]" in A:
                            print("watchout-electrolyzer is acting weird")
                        else:
                            print("other component is acting werid")


                    if "AdvancedBattery - AC Battery Power [Electricity - W]" in A:
                        sum_Demand_Battery= sum(x for x in A["AdvancedBattery - AC Battery Power [Electricity - W]"] if x > 0)
                    else:
                        sum_Demand_Battery = 0
                    if "AdvancedBattery - AC Battery Power [Electricity - W]" in A:
                        sum_Produced_Elect_Battery= sum(x for x in A["AdvancedBattery - AC Battery Power [Electricity - W]"] if x < 0)
                    else:
                        sum_Produced_Elect_Battery = 0

                    if "HeatPumpHplib - ElectricalInputPower [Electricity - W]" in A:
                        sum_Demand_Elect_heat_pump= sum((A["HeatPumpHplib - ElectricalInputPower [Electricity - W]"]))
                    else:
                        sum_Demand_Elect_heat_pump = 0

                    if "Electrolyzer - Unused Power [Electricity - W]" in A:
                        sum_Demand_Elect_electrolyzer= sum((A["Controller - ElectricityToElectrolyzerTarget [Electricity - W]"])) - sum((A["Electrolyzer - Unused Power [Electricity - W]"]))

                    else:
                        sum_Demand_Elect_electrolyzer = 0

                    if "CHP - ElectricityOutput [Electricity - W]" in A:
                        sum_Produced_Elect_chp= sum((A["CHP - ElectricityOutput [Electricity - W]"]))
                    else:
                        sum_Produced_Elect_chp = 0

                    sum_Demand=sum_Demand_Elect_heat_pump+sum_Demand_Elect_house+sum_Demand_Elect_electrolyzer+sum_Demand_Battery
                    sum_Produced=sum_Produced_Elect_pv+sum_Produced_Elect_Battery+sum_Produced_Elect_chp
                    own_consumption=(sum_Produced_Elect_pv-sum_Electricity_Into_Grid)/(sum_Produced_Elect_pv)
                    autarky=(sum_Demand_Elect_house - sum_Electricity_From_Grid) / (sum_Demand_Elect_house)
                    if own_consumption > 1:
                        print("owncumption is bigger than one :" +str(own_consumption))
                        own_consumption=1
                    elif own_consumption <  0:
                        print("owncumption is smaller than one :" + str(own_consumption))
                        own_consumption=0.001
                    if autarky > 1:
                        print("autarky is bigger than one :" +str(autarky))
                        autarky=1
                    elif autarky <  0:
                        print("autarky is smaller than one :" + str(autarky))
                        autarky=0.001

                    newrow.append(own_consumption) #own_consumption
                    newrow.append(autarky) #autarky
                    key_performance_indicators = np.vstack([key_performance_indicators, newrow])

            except OSError:
                print("Error:not found: "+(os.path.join(globals.HISIMPATH["results"], ""+str(new_list[a])+"/"+str(self.pickle_file_name)+".pickle"))+"")
                continue
        return key_performance_indicators


    def transform_data_for_plot(self,target_matrix,key_performance_indicators,kpi,component):
        breaker=False
        num_rows, num_cols = target_matrix.shape
        if num_rows ==1:
            breaker=True
            return 0, 0 ,0, breaker
        x = 0
        x_axis = []
        y_axis = []
        own_consumption = []
        autarky = []
        while x < (num_rows - 1):
            x = x + 1
            if component in "plot_battery_and_pv":
                x_axis.append((target_matrix[x, 5] / 1000) / target_matrix[x, 4])  # in kW/kW
                y_axis.append(target_matrix[x, 6] / (target_matrix[x, 4]))  # in kWh/kw
            elif component in "plot_h2_storage":
                if target_matrix[x, 13] == None or target_matrix[x, 13] == 0:
                    breaker = True
                    return 1, 0 ,0, breaker
                else:
                    x_axis.append((target_matrix[x, 5]/1000) / target_matrix[x, 6])  # in kW/kW
                    y_axis.append(target_matrix[x, 13]/(target_matrix[x, 4])) # in kWh/kw
            else:
                print("no component to print choosed")
        x_axis = np.around(np.array(x_axis), decimals=2)
        y_axis = np.around(np.array(y_axis), decimals=2)
        if kpi == "OwnConsumption":
            key_to_look_at = key_performance_indicators[1::, 0]
        elif kpi == "Autarky":
            key_to_look_at = key_performance_indicators[1::, 1]

        # Set up Matrix and fill with values-Has to be done bec. of Latin Hypercube design
        plot_boundaries = [[((min(x_axis))), (max(x_axis))],
                           [(min(y_axis)), (max(y_axis))]]
        precision_x_axis = (plot_boundaries[(0)][1] - plot_boundaries[(0)][0]) / self.heat_map_precision_factor
        precision_y_axis = (plot_boundaries[(1)][1] - plot_boundaries[(1)][0]) / self.heat_map_precision_factor
        grid = np.full([self.heat_map_precision_factor+1, self.heat_map_precision_factor+1], 0.0)
        x = 0
        while x < (len(x_axis)):
            x_index = round((x_axis[x] - plot_boundaries[(0)][0]) / precision_x_axis)
            y_index = round((y_axis[x] - plot_boundaries[(1)][0]) / precision_y_axis)
            if float(key_to_look_at[x])>0.9:
                print(key_to_look_at[x])


            if grid[y_index, x_index] == 0:
                grid[y_index, x_index] = float(key_to_look_at[x])
            else:
                grid[y_index, x_index] = (grid[y_index, x_index]) #+ float(key_to_look_at[x])) / 2
            x = x + 1
        Z =grid
        x= np.arange (plot_boundaries[(0)][0], plot_boundaries[(0)][1], precision_x_axis)
        y= np.arange (plot_boundaries[(1)][0], plot_boundaries[(1)][1], precision_y_axis)
        return Z, x, y, breaker


    def sort_out_because_of_house_choosing(self,target_matrix,key_performance_indicators,x ):
        breaker= False
        if x=="plot_all_houses":
            target_matrix_new = target_matrix
            key_performance_indicators_new = key_performance_indicators
        elif x=="plot_sfh":
            target_matrix_new = np.delete(target_matrix, np.where(target_matrix == "mfh")[0], 0)
            key_performance_indicators_new = np.delete(key_performance_indicators,
                                                       np.where(target_matrix == "mfh")[0], 0)

        elif x=="plot_mfh":
            target_matrix_new = np.delete(target_matrix, np.where(target_matrix == "sfh")[0], 0)
            key_performance_indicators_new = np.delete(key_performance_indicators,
                                                       np.where(target_matrix == "sfh")[0], 0)
        else:
            breaker= True
            return 0 , 0 , breaker
        return target_matrix_new, key_performance_indicators_new, breaker
    def sort_out_because_of_strategy_choosing(self,target_matrix,key_performance_indicators,y):
        breaker= False
        if y=="plot_strategy_all":
            target_matrix_new = target_matrix.copy()
            key_performance_indicators_new = key_performance_indicators.copy()
        elif y=="plot_strategy_own_consumption":

            B =(target_matrix[np.any(target_matrix == "Weather", axis=1)])
            A = (target_matrix[np.any(target_matrix == "optimize_own_consumption", axis=1)])
            target_matrix_new=np.append(B,A,axis=0)

            C = key_performance_indicators.copy()
            i=0
            while i < (len(target_matrix[:,14])-1):
                i=i+1
                if target_matrix[i,14] != "optimize_own_consumption":
                    C[i,0] = "delete"
            key_performance_indicators_new = np.delete(C, np.where(C == "delete")[0], 0)






        elif y=="plot_strategy_seasonal_storage":

            B =(target_matrix[np.any(target_matrix == "Weather", axis=1)])
            A = (target_matrix[np.any(target_matrix == "seasonal_storage", axis=1)])
            target_matrix_new=np.append(B,A,axis=0)
            key_performance_indicators_new=key_performance_indicators.copy()
            i=0
            while i < (len(target_matrix[:,14])-1):
                i=i+1
                if target_matrix[i,14] != "seasonal_storage":
                    key_performance_indicators_new[i,0] = "delete"

            key_performance_indicators_new = np.delete(key_performance_indicators_new, np.where(key_performance_indicators_new == "delete")[0], 0)


        elif y=="plot_strategy_peak_shave_into_grid":

            B =(target_matrix[np.any(target_matrix == "Weather", axis=1)])
            A = (target_matrix[np.any(target_matrix == "peak_shaving_into_grid", axis=1)])
            target_matrix_new=np.append(B,A,axis=0)
            key_performance_indicators_new=key_performance_indicators.copy()
            i=0
            while i < (len(target_matrix[:,14])-1):
                i=i+1
                if target_matrix[i,14] != "peak_shaving_into_grid":
                    key_performance_indicators_new[i,0] = "delete"

            key_performance_indicators_new = np.delete(key_performance_indicators_new, np.where(key_performance_indicators_new == "delete")[0], 0)
        else:
            breaker= True
            return 0, 0, breaker
        #elif self.flags["plot_strategy_peak_shave_into_grid"]:
            #pass
        return target_matrix_new , key_performance_indicators_new, breaker
    def plot_heat_map(self,target_matrix,key_performance_indicators):

        for kpi in key_performance_indicators[0,:]:
            for house in self.flags_houses:
                target_matrix_new_after_house, key_performance_indicators_new_after_house, breaker=self.sort_out_because_of_house_choosing(target_matrix=target_matrix,key_performance_indicators=key_performance_indicators, x=house)
                if breaker:
                    continue
                for strategy in self.flags_strategy:
                    target_matrix_after_stragey, key_performance_indicators_new_after_strategy, breaker= self.sort_out_because_of_strategy_choosing(target_matrix=target_matrix_new_after_house, key_performance_indicators=key_performance_indicators_new_after_house,y=strategy )
                    if breaker:
                        continue
                    for component in self.flags_components:

                        Z, x ,y, breaker=self.transform_data_for_plot(target_matrix=target_matrix_after_stragey, key_performance_indicators=key_performance_indicators_new_after_strategy,kpi=kpi,component=component)
                        if breaker == True and Z==0:
                            print(""+house+" with "+strategy+" has no simulation results and can't be printed")
                            continue
                        elif breaker == True and Z==1:
                            continue
                        fig, ax = plt.subplots()
                        cax=ax.pcolormesh(Z,cmap="YlGnBu",vmin=0)   #vmax=1 for own consumption good
                        cbar = fig.colorbar(cax)
                        cbar.ax.set_ylabel(kpi)


                        ax.set_xticklabels((list(np.round(x,1))))
                        ax.set_yticklabels((list(np.round(y,1))))
                        ax.set_title("" + house + " with " + strategy + "")
                        #ax.set_xticklabels(xticklabels)

                        if component == "plot_h2_storage":
                            plt.xlabel('PV-Power kWp/Battery-Capacity kWh')
                            plt.ylabel('H2 Storage in litres / MWh')
                            plt.show()
                        else:
                            plt.xlabel('PV-Power kWp/MWh')
                            plt.ylabel('Battery-Capacity kWh/MWh')
                            plt.show()
                    #hier ne ebsser Abrufung bauen!!!!





                    '''
                    fig, ax = plt.subplots()
                    sns.set_theme()
                    uniform_data = Z
                    sns.heatmap(uniform_data,vmin=0, vmax=1, cbar_kws={'label': kpi}, cmap="YlGnBu")
                    ax.set(xlabel='PV-Power kWp/MWh', ylabel='Battery-Capacity kWp/MWh')
                    ax.set_title(""+house+" with " +strategy+"")
                    ax.set_xlim(min(x),max(x))
                    ax.set_xticks(range(0,int(max(x))))

                    ax.set_ylim(min(y), max(y))
                    ax.set_yticks(range(0,int(max(y))))

                    ax.invert_yaxis()

                    plt.show()
                    '''






    def run(self):
        #I am working with numpy array instead of dict, bec. can be made better to grafics.
        #Names are not consistent in Components, so hard to automize
        target_matrix= np.array(["Weather",
                                 "HouseType",
                                 "WarmWaterDemand",
                                 "HeatingWaterDemand",
                                 "ElectricityDemand",
                                 "PVSystemPower",
                                 "BatteryCapacity",
                                 "HeatPumpPower",
                                 "GasHeaterPower",
                                 "CHPPower",
                                 "ElectrolyzerPower",
                                 "HeatStorageVolume",
                                 "WarmWaterStorageVolume",
                                 "HydrogenStorageVolume",
                                 "ControlStrategy",
                                 "PercentageToShave"])

        key_performance_indicators=np.array(["OwnConsumption",
                                             "Autarky"])
        new_list = self.get_all_relevant_folders()
        target_matrix=self.get_json_data(new_list,target_matrix)
        key_performance_indicators=self.get_pickle_informations(new_list,key_performance_indicators,target_matrix)
        self.plot_heat_map(target_matrix,key_performance_indicators)



my_Post_Processor=PostProcessor(folder_name="basic_household_implicit_hyper_cube_",
                                json_file_name="cfg",
                                pickle_file_name="data",
                                start_date="20211118_122200",
                                end_date="20211118_234900",
                                heat_map_precision_factor=20)
my_Post_Processor.run()
#f=open("HiSim/hisim/results/basic_household_implicit_hyper_cube_20211113_130857/cfg.json",)
#data = json.load(f)

