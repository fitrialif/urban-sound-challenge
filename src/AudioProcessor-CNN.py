"""
Urban Sound Challenge - Sound Classification using Convolutional Neural Network (CNN)
@author: - Hitesh Bagchi
Version: 1.0
Date: 25th June 2018
"""
#--------------------------------------------------------------------------------------------------
# Python libraries import
#--------------------------------------------------------------------------------------------------
import os
from pathlib import Path

import librosa
import pandas as pd
import numpy as np
from functools import partial
from sklearn.preprocessing import LabelEncoder

from keras.models import Sequential
from keras.layers import Dense, Dropout, Activation

from keras.utils import np_utils

# %%
def windows(data, window_size):
    start = 0
    while start < len(data):
        yield int(start), int(start + window_size)
        start += (window_size / 2)

# %%
#--------------------------------------------------------------------------------------------------
# function to load files and extract features
#--------------------------------------------------------------------------------------------------
def extract_features(data_dir, row, bands = 60, frames = 41, file_ext="*.wav"):

    window_size = 512 * (frames - 1)
    log_specgrams = []

    file_name = os.path.join(os.path.abspath('./data/'), data_dir, str(row.ID) + '.wav')

    # handle exception to check for corrupted or invalid file
    try:
        X, sample_rate = librosa.load(file_name)

        for (start, end) in windows(X, window_size):
            if(len(X[start:end]) == window_size):
                signal = X[start:end]
                melspec = librosa.feature.melspectrogram(signal, n_mels = bands)
                logspec = librosa.amplitude_to_db(melspec)
                logspec = logspec.T.flatten()[:, np.newaxis].T
                log_specgrams.append(logspec)

        log_specgrams = np.asarray(log_specgrams).reshape(len(log_specgrams),bands,frames, 1)
        features = np.concatenate((log_specgrams, np.zeros(np.shape(log_specgrams))), axis = 3)

        for i in range(len(features)):
            features[i, :, :, 1] = librosa.feature.delta(features[i, :, :, 0])

    except Exception as e:
        print(file_name, e)
        return None

    return features

# %%
def dump_features(features, features_filename):
    features_df = pd.DataFrame(features)
    features_df.to_pickle(features_filename)

# %%
#------------------------------------------------------------------------------
# Load training data and extract features
#------------------------------------------------------------------------------
DATA_DIR = 'trainMini'

train = pd.read_csv(os.path.join(os.path.abspath('./data/'), DATA_DIR + '.csv'))

features_cnn_train_file = Path("./features_cnn_train.pkl")

if not features_cnn_train_file.is_file():
    extract_features_train = partial(extract_features, DATA_DIR)
    features = train.apply(extract_features_train, axis=1)
    dump_features(features, features_cnn_train_file)
    train = train.assign(features=features.values)
else:
    features = pd.read_pickle('./features_cnn_train.pkl')
    train = train.assign(features=features.values)

# %%
y = np.array(train.loc[:, 'Class'])
lb = LabelEncoder()
y = np_utils.to_categorical(lb.fit_transform(y))

X = np.array(train.loc[:, 'features'])
X = np.vstack(X)

# %%
num_labels = y.shape[1] # Toral number of output labels
num_inputs = X.shape[1] # Total number 0f input variables

# build model
model = Sequential()

# Input layer
model.add(Dense(156, input_shape=(num_inputs,)))
model.add(Activation('relu'))
model.add(Dropout(0.25))

# Hidden layer
model.add(Dense(156))
model.add(Activation('relu'))
model.add(Dropout(0.25))

# Output layer
model.add(Dense(num_labels))
model.add(Activation('softmax'))

# Compile model
model.compile(loss='categorical_crossentropy', metrics=['accuracy'], optimizer='adam')
