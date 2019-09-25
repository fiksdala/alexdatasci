This folder contains all files necessary to get predictions on a dataset in an identical format (and with the same variables) as the training dataset. It also contains a Jupyter Notebook (data_challenge.ipynb) that outlines my analysis process, along with some other pickled files that are required to get predictions. Follow the directions below to run the model and get predictions:

1. Requirements: Modules from the following libraries will be imported when generating predictions and must be installed:
    - pickle
    - pandas
    - numpy
    - sklearn
2. Place the test dataframe in this folder, and rename it as 'test_data.csv'
3. From the terminal, change directory to this folder
4. Type the following to run the file: python get_predictions.py
5. A new .csv file with predictions 'test_predictions.csv' will appear when the script is done running.

NOTES: 

*This script has not been optimized for speed and involves many variable transformations and dataframe reshaping operations. It may take 5-10 minutes for the entire script to run.

*I used the following version of python. Different versions may affect compatibility:
Python 3.6.8 :: Anaconda custom (64-bit)



