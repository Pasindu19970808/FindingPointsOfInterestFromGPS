import numpy as np
import pandas as pd
from .basefuncs import obtain_daily_trajectory,obtain_mpd_trajectory,detect_stops,plotTrajectoryWithStops
from .trajectoryClass import Trajectory
import time



class UUID:
    def __init__(self,id,trajectory,plot_map):
        assert isinstance(trajectory,Trajectory),"Invalid Trajectory Type"
        self.id = id
        self.trajectory = trajectory
        self.geodataframe_trajectory = self.trajectory.trajectory
        self.plot_map = plot_map
        #holds the daily trajectories with stop labels
        self.parent_trajectory_with_stop_labels = {}
        #holds the map of each trajectory
        if self.plot_map:
            self.daily_trajectory_map = {}
        #holds the Moving Pandas stop point GeoDataFrame = {}
        self.mpd_stop_points = {}
    def process_trajectory(self,min_duration,max_diameter):
        # start_time = time.time()
        #daily trajectories contains the daily geodataframe with geometry and all column from rquired columns
        daily_trajectories = obtain_daily_trajectory(self.geodataframe_trajectory)
        #Makes a MovingPandas Trajectory
        daily_mpd_trajectories = obtain_mpd_trajectory(daily_trajectories)
        for date in daily_mpd_trajectories:
            #Detects the stops using the movingpandas trajectory
            stop_points = detect_stops(daily_mpd_trajectories[date],min_duration,max_diameter)
            trajectory_with_stops,map = plotTrajectoryWithStops(stop_points,daily_trajectories[date],self.plot_map)
            self.parent_trajectory_with_stop_labels[date] = trajectory_with_stops
            if self.plot_map:
                self.daily_trajectory_map[date] = map
            #collects every stop point of the daily trajectory
            ###IMPORTANT###
            ###IF YOU WANT TO ANALYSE THE DATA OF A SINGLE TRAJECTORY, EXTRACT THIS###
            ###THEN PASS THE GEOPANDASFRAME INTO THE EXTRACTANDORGANIZE CLASS###
            self.mpd_stop_points[date] = stop_points
        # print(f"Finished {self.id} in {time.time() - start_time}")

        

class UUIDCollection:
    def __init__(self,data,
                 unique_identifier_col,
                 index_col,
                 sort_values_col,
                 lat_col,
                 long_col,
                 required_cols,
                 min_duration,
                 max_diameter,
                 min_points = None,
                 query_amount = None,
                 plot_map = False):
        """
        data : Pandas Dataframe containing all the latitude and longitudes
        index_col : column to be made into DateTime Index. Each value needs to be of Timestamp 
        sort_values_col : column to sort trajectories on
        lat_col : name of latitude containing column
        long_col : name of longitude containing column

        """
        ### HEIRARCHY ###
        ### Raw Dataframe -> Group by unique UUID -> Make Trajectory Object -> Send Trajectory object to make UUID object ###
        ### UUID Object will process to each data ###

        assert isinstance(data,pd.DataFrame),TypeError("data argument needs to be of pd.DataFrame type")
        assert unique_identifier_col in data.columns,KeyError(f"{unique_identifier_col} not available in Column list")
        assert index_col in data.columns,KeyError(f"{index_col} not available in Column list")
        assert sort_values_col in data.columns,KeyError(f"{sort_values_col} not available in Column list")
        assert lat_col in data.columns,KeyError(f"{lat_col} not available in Column list")
        assert long_col in data.columns,KeyError(f"{long_col} not available in Column list")
        assert isinstance(required_cols,list),TypeError("required_col argument needs to be a list")

        self.unique_col = unique_identifier_col
        self.index_col = index_col
        self.sort_values = sort_values_col
        self.lat_col = lat_col
        self.long_col = long_col
        self.required_cols = required_cols
        self.min_duration = min_duration
        self.max_diameter = max_diameter
        self.min_points = min_points
        self.random_seed = 42
        self.query_amount = query_amount
        self.plot_map = plot_map
        #collect ech UUIDs entire trajectory
        uuid_trajectory_objects = self._collect_uuids(data,required_cols)
        
        #Get trajectories having more that min_points
        if min_points:
            self.uuid_trajectory_objects = self._filter_on_size(uuid_trajectory_objects,self.min_points)
        else:
            self.uuid_trajectory_objects = uuid_trajectory_objects
        print("Finished making Trajectory Objects")

        
        self.uuid_collection = self._process_trajectory(self.uuid_trajectory_objects,self.query_amount)
        self.complete_traj_stop_df = self._concatenate_uuids_to_one_df(self.uuid_collection)
        
        

    def _collect_uuids(self,data,required_cols):
        trajectory_dict = {}
        for k,grp in data.groupby(self.unique_col):
            #Collects each person's entire trajectory
            col = required_cols.copy()
            #Trajectory Object
            trajectory_dict[k] = Trajectory(grp.sort_values(by =  self.sort_values).set_index(self.index_col),self.lat_col,self.long_col,col)
        
        return trajectory_dict
    def _filter_on_size(self,trajectory_objects,min_points):
        #val is the Trajectory Object with the shape
        filtered_trajectory_dict = {key:val for key,val in trajectory_objects.items() if len(val) > min_points}

        return filtered_trajectory_dict
    
    def _sample_uuids(self,query_amount):
        #selects random UUIDs to be included in the investigation
        #all the UUIDs coming here have min_points or above coordinates
        uuid_list = list(self.uuid_trajectory_objects.keys())
        selected_uuids = []
        np.random.seed(self.random_seed)
        assert query_amount < len(uuid_list),"Query amount cannot be larger than the number of available unique UUIDs"
        while len(selected_uuids) < query_amount:
            idx = np.random.choice(len(uuid_list))
            if uuid_list[idx] not in selected_uuids:
                selected_uuids.append(uuid_list[idx])
        return selected_uuids

    def _process_trajectory(self,trajectory_objects,query_amount):
        sampled_uuids = None
        if query_amount:
            sampled_uuids = self._sample_uuids(query_amount)

        uuid_dict = {}
        print("Starting to Get Stop Points for Every UUID")
        if sampled_uuids:
            for k in sampled_uuids:
                #Put the trajectory for each UUID
                uuid_obj = UUID(k,trajectory_objects[k],self.plot_map)
                #Obtains
                #1) THe daily trajectory
                #2) Stops in daily trajectory
                uuid_obj.process_trajectory(self.min_duration,self.max_diameter)
                uuid_dict[k] = uuid_obj
        else:
            for k,trajectory in trajectory_objects.items():
                uuid_obj = UUID(k,trajectory,self.plot_map)
                uuid_obj.process_trajectory(self.min_duration,self.max_diameter)
                uuid_dict[k] = uuid_obj
        print("Finished Getting Stop Points for Every UUID")
        return uuid_dict
    def _concatenate_uuids_to_one_df(self,uuid_collection:dict):
        #This df will contain gpsacc,Stop Or Moving,geometry,UUID
        df_list = []
        for uuid,uuid_obj in uuid_collection.items():
            full_trajectory = uuid_obj.parent_trajectory_with_stop_labels #this is also a dictionary containing the daily trajectory
            for date,traj_df in full_trajectory.items():
                traj_df = traj_df.reset_index()
                traj_df[self.unique_col] = [uuid]*traj_df.shape[0]
                df_list.append(traj_df)
        concat_df = pd.concat(df_list,axis = 0)
        concat_df = concat_df.reset_index(drop = True)
        return concat_df
