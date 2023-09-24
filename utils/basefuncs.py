import pandas as pd
import numpy as np
from pathlib import Path
import os
from typing import List
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
    def processTimeStamp(self,df:pd.DataFrame,col_name:str,unit:str,funcs : listStr,new_cols:listStr):
        assert len(funcs) == len(new_cols),f"Mismatch in number of functions (funcs) and column names(new_cols) : {len(funcs)} vs {len(new_cols)}"
        time_df = pd.DataFrame({},columns=new_cols)
        for func,new_col in zip(funcs,new_cols):
            time_df[new_col] = pd.to_datetime(df[col_name],unit = unit).apply(func= lambda x : getattr(x,func))
        time_df[col_name] = pd.to_datetime(df[col_name],unit=unit)
        return df,time_df
    def combineDF(self,df,time_df,col_order : listStr = None):
        if col_order is None:
            col_order = df.columns.tolist()
            col_order.extend(time_df.columns.tolist())
        return pd.concat([df,time_df],axis = 1)[col_order]
    def processDF(self):
        df = self.readDataFrame(**self.variable_dictionary['readDataFrame'])
        df,time_df = self.processTimeStamp(df,**self.variable_dictionary['processTimeStamp'])
        df = self.combineDF(df,time_df,**self.variable_dictionary['combineDF'])
        return df
        

