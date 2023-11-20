import pandas as pd
import numpy as np
from pathlib import Path
import os
from typing import List,Union
import movingpandas as mpd
import folium




class obtainUserInput:
    def __init__(self,filepath,sheet_name):
        self.filepath = filepath
        self.sheet_name = sheet_name
    def obtainVariables(self):
        variable_dictionary = {}
        df = pd.read_excel(self.filepath,sheet_name=self.sheet_name)
        process_func = lambda x : x.tolist() if x.shape[0] > 1 else x.values[0]
        for key,grp in df.groupby('FunctionName'):
            variable_dictionary[key] = {k:process_func(grpsub['VariableValue']) for k,grpsub in grp.groupby('VariableName')}
        return variable_dictionary
class mainClass:
    def __init__(self,path,sheetname):
        self.path = path
        self.sheetname = sheetname
        self.variable_dictionary = obtainUserInput(self.path,self.sheetname).obtainVariables()
    def readDataFrame(self,data_path):
        return pd.read_csv(data_path)

class preProcessDataFrame(mainClass):
    listStr = List[str]
    def processTimeStamp(self,df:pd.DataFrame,col_name:Union[str,listStr],unit:str,funcs : listStr,new_cols:listStr):
        assert len(funcs) == len(new_cols),f"Mismatch in number of functions (funcs) and column names(new_cols) : {len(funcs)} vs {len(new_cols)}"
        
        col_name = [col_name] if isinstance(col_name,str) else col_name
        time_df = pd.DataFrame({})
        for col in col_name:
            col_time = pd.to_datetime(df[col],unit = unit,errors = 'coerce')
            for func,new_col in zip(funcs,new_cols):
                time_df[f"{col}_{new_col}"] = col_time.apply(func= lambda x : getattr(x,func))
            time_df[col] = col_time
        df.drop(col_name,axis = 1,inplace = True)
        return df,time_df
    def combineDF(self,df,time_df,col_order : listStr = None):
        if col_order is None:
            col_order = df.columns.tolist()
        col_order.extend(time_df.columns.tolist())
        return pd.concat([df,time_df],axis = 1)[col_order]
    def filterLatLong(self,df,lat_col,long_col,latmin,latmax,longmin,longmax):
        df = df.loc[~((df[lat_col] < latmin) | (df[lat_col] > latmax))]
        df = df.loc[~((df[long_col]<longmin) | (df[long_col]> longmax))]
        df = df.reset_index(drop = True)
        return df


    def processDF(self):
        df = self.readDataFrame(**self.variable_dictionary['readDataFrame'])
        df = self.filterLatLong(df,**self.variable_dictionary['filterLatLong'])
        df,time_df = self.processTimeStamp(df,**self.variable_dictionary['processTimeStamp'])
        df = self.combineDF(df,time_df,**self.variable_dictionary['combineDF'])
        return df
    

def obtain_daily_trajectory(complete_traj):
    complete_traj['grouping_col'] = complete_traj.index.values
    result = {}
    for k,daily_traj in complete_traj.groupby(pd.Grouper(key = 'grouping_col',freq = 'D')):
        if daily_traj.shape[0] > 2:
            result[str(k.date())] = daily_traj[[i for i in daily_traj.columns if i != 'grouping_col']]
    return result

def obtain_mpd_trajectory(trajectory_dict):
    return {k:mpd.Trajectory(daily_traj[[daily_traj.geometry.name]],traj_id=k) for k,daily_traj in trajectory_dict.items()}
    
def makeFoliumMap(trajectory):
    map = folium.Map([22.3193,114.1694],zoom_start=12)
    for x in trajectory.to_dict(orient = 'records'):
        long = x['geometry'].x
        lat = x['geometry'].y
        if x['Stop Or Moving'] == 'S':
            folium.CircleMarker(location = [lat,long],radius = 10,fill_color = 'red').add_to(map)
        else:
            folium.CircleMarker(location = [lat,long],radius = 10,fill_color = 'blue',).add_to(map)
    return map

def plotTrajectoryWithStops(stop_time_ranges,trajectory,plot_map):
    trajectory['Stop Or Moving'] = ['M'] * trajectory.shape[0]
    for x in stop_time_ranges.to_dict(orient = 'records'):
        trajectory.loc[x['start_time']:x['end_time'],'Stop Or Moving'] = 'S'
    if plot_map is True:
        map = makeFoliumMap(trajectory)
        return trajectory,map
    else:
        return trajectory,None

def detect_stops(trajectory,min_duration,max_diameter):
    detector = mpd.TrajectoryStopDetector(trajectory)
    stop_points = detector.get_stop_points(min_duration=min_duration,max_diameter=max_diameter)
    if stop_points.shape[0] >= 1:
        stop_points.reset_index(drop = True)
        #this is not the trajectory to send. instead send from daily trajectory
    return stop_points


        

