#!/usr/bin/env python
# coding: utf-8

# In[1]:


import pandas as pd
import os
from functools import reduce


# In[2]:


idle_file_directory = "../data/idle/"
attack_file_directory = "../data/spectre/"

combined_directory = "../data/combined data files/"

idle_run_folders = [d for d in os.listdir(idle_file_directory) if os.path.isdir(os.path.join(idle_file_directory, d))]
attack_run_folders = [d for d in os.listdir(attack_file_directory) if os.path.isdir(os.path.join(attack_file_directory, d))]



def getBatchFileInDirectory(path,folder):
    finalpath = os.path.join(path,folder,"csv")
    if os.path.isdir(finalpath):
        # Get the list of files in the final path
        batch_files = [f for f in os.listdir(finalpath) if os.path.isfile(os.path.join(finalpath, f))]
        return batch_files
    else:
        # Return an empty list if the path does not exist or is not a directory
        return []

def getExecutedFolders(file_path):
    executed_folders = []
    try:
        with open(file_path, 'r') as file:
            # Read each line and strip any whitespace or newline characters
            executed_folders = [line.strip() for line in file if line.strip()]
    except FileNotFoundError:
        print(f"The file {file_path} was not found.")
    except IOError:
        print(f"An error occurred while reading the file {file_path}.")
    return executed_folders
    
def getValidFolders(folders,isIdle):
    valid_folders = []
    executed_folders_path = (idle_file_directory if isIdle else attack_file_directory) + "executed_folders.txt"
    executed_folders = getExecutedFolders(executed_folders_path)
    for folder in folders:
        if folder in executed_folders:
            print(f"Folder '{folder}' has already been executed. Hence Skipping")
        else:
            print(f"Folder '{folder}' has not been executed. Hence Vaild")
            valid_folders.append(folder)
    
    return valid_folders


def getValidBatchFiles(isIdle):
    # Determine folders and path based on isIdle
    folders = idle_run_folders if isIdle else attack_run_folders
    path = idle_file_directory if isIdle else attack_file_directory

    # Get the valid folders that haven't been executed
    valid_folders = getValidFolders(folders, isIdle)

    # Initialize a list to store batch paths and files as key-value pairs
    validBatchFiles = []

    # Iterate over each valid folder
    for folder in valid_folders:
        # Get batch files and batch path
        batch_files = getBatchFileInDirectory(path, folder)
        batchPath = os.path.join(path, folder, "csv")

        # Store batch path and files as a dictionary in validBatchFiles
        validBatchFiles.append({batchPath: batch_files})

    return validBatchFiles

def validBatchPath(batchPath, batch_files):
    # Generate full paths by joining batchPath with each file name in batch_files
    complete_paths = [os.path.join(batchPath, file) for file in batch_files]
    return complete_paths

def loadBatchFilesAsDataFrames(batchPath, batch_files):
    batch_dataframes = {}
    batch_count = 1  # Counter to label batch files sequentially

    for file in batch_files:
        file_path = os.path.join(batchPath, file)
        
        # Check if the file is a default file
        if "default" in file:
            key = "default"
        # Check if the file is a batch file and assign a batch key sequentially
        elif "batch" in file:
            key = f"batch_{batch_count}"
            batch_count += 1
        else:
            # Skip files that do not match the expected naming convention
            continue

        # Load the CSV file as a DataFrame and add it to the dictionary
        batch_dataframes[key] = pd.read_csv(file_path)

    return batch_dataframes

def cleanupBatchFile(df):
    # Step 1: Drop columns where all values are zero
    df = df.loc[:, (df != 0).any(axis=0)].copy()  # Make a copy to avoid SettingWithCopyWarning
    
    # Step 2: Reset the index column to start at 0 and retain increments
    index_column_name = df.columns[0]
    df.loc[:, index_column_name] = df[index_column_name] - df[index_column_name].iloc[0]
    
    return df

def loadAndCleanBatchFiles(batchPath, batch_files):
    # Load the batch files using the provided function
    batch_dataframes = loadBatchFilesAsDataFrames(batchPath, batch_files)
    
    # Dictionary to store cleaned DataFrames
    cleaned_up_batch_dataframes = {}
    
    # Apply cleaning to each loaded DataFrame
    for key, df in batch_dataframes.items():
        cleaned_up_batch_dataframes[key] = cleanupBatchFile(df)
    
    return cleaned_up_batch_dataframes

def generateMasterDataFrame(cleaned_up_batch_dataframes):
    # Merge all DataFrames on the 'index' column using an outer join to keep all rows
    dataframes = list(cleaned_up_batch_dataframes.values())
    master_df = reduce(lambda left, right: pd.merge(left, right, on='index', how='outer'), dataframes)
    
    # Sort by 'index' column and reset the DataFrame index
    master_df.sort_values(by='index', inplace=True)
    master_df.reset_index(drop=True, inplace=True)
    
    # Fill NaN values with 0
    master_df.fillna(0, inplace=True)
    
    # Convert all columns to integers
    master_df = master_df.astype(int)
    
    return master_df

def saveMasterDataFrame(master_df, attack_type, filename):
    # Create the output path
    output_path = os.path.join(combined_directory, attack_type, f"{filename}.csv")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)  # Create directories if not exist
    
    # Save the master DataFrame to the specified CSV location
    master_df.to_csv(output_path, index=False)
    print(f"Master DataFrame saved to {output_path}")
    
def addFolderNameToExecutedFolders(executed_folders_path, folder_name):
    with open(executed_folders_path, 'a') as file:
        file.write(f"{folder_name}\n")
    print(f"Added '{folder_name}' to executed_folders.txt")
    
def processBatches(isIdle):
    valid_batch_files = getValidBatchFiles(isIdle)

    for batch_dict in valid_batch_files:
        for batchPath, batch_files in batch_dict.items():

            parent_path = os.path.dirname(batchPath)
            # Extract the folder name
            folder_name = os.path.basename(parent_path)

            attackType = "Idle" if isIdle else "Spectre"

            print(f"Proxessing Folder: ",folder_name," for AttackType: ",attackType)
            clean_batches = loadAndCleanBatchFiles(batchPath, batch_files)
            master_df = generateMasterDataFrame(clean_batches)

            fileName = attackType+"_" + folder_name
            saveMasterDataFrame(master_df,attackType,fileName)
            print(f"Proxessing Folder: ",folder_name," for AttackType: ",attackType,"Completed Sucessfully")
            executed_folders_path = (idle_file_directory if isIdle else attack_file_directory) + "executed_folders.txt"
            addFolderNameToExecutedFolders(executed_folders_path, folder_name)

            
isIdle = False
print("processing Spectre Files")
processBatches(isIdle)

isIdle = True


print("processing Idle Files")
processBatches(isIdle)


# In[ ]:




