#--------------------------------------------------------------------------------------------------
# Python libraries import
#--------------------------------------------------------------------------------------------------
import numpy as np
import os
from pathlib import Path
import pandas as pd
import librosa, librosa.display

from sklearn.preprocessing import LabelEncoder

from keras.models import Sequential
from keras.layers import Dense, Dropout, Activation
from keras.utils.vis_utils import model_to_dot
from keras.utils import np_utils

import matplotlib.pyplot as plt
plt.rcParams.update({'figure.max_open_warning': 0})

from matplotlib.pyplot import specgram

from IPython.display import SVG

# %%
#--------------------------------------------------------------------------------------------------
# Data Exploration
#--------------------------------------------------------------------------------------------------
def load_sample_audios(train):
    sample = train.groupby('Class', as_index=False).agg(np.random.choice)
    raw_audios = []
    class_audios = []
    for i in range(0, len(sample)):
        x, sr = librosa.load('./data/train/' + str(sample.ID[i]) + '.wav')
        x = librosa.resample(x, sr, 22050)
        raw_audios.append(x)
        class_audios.append(sample.Class[i])
    return class_audios, raw_audios

# Plot Waveplot
def plot_waves(class_audios, raw_audios):
    for x, label in zip(raw_audios, class_audios):
        plt.figure(figsize=(8, 20))
        plt.subplot(10, 1, class_audios.index(label)+1)
        librosa.display.waveplot(x)
        plt.title(label)

# Plot Specgram
def plot_specgram(class_audios, raw_audios):
    for x, label in zip(raw_audios, class_audios):
        plt.figure(figsize=(8, 40))
        plt.subplot(10, 1, class_audios.index(label)+1)
        specgram(x, Fs=22050)
        plt.title(label)

# Plot log power specgram
def plot_log_power_specgram(class_audios, raw_audios):
    for x, label in zip(raw_audios, class_audios):
        plt.figure(figsize=(8, 40))
        plt.subplot(10, 1, class_audios.index(label)+1)
        D = librosa.amplitude_to_db(np.abs(librosa.stft(x))**2, ref=np.max)
        librosa.display.specshow(D, x_axis='time', y_axis='log')
        plt.title(label)


# data directory and csv file should have the same name
DATA_PATH = 'train'

train = pd.read_csv('./data/' + DATA_PATH + '.csv')

class_audios, raw_audios = load_sample_audios(train)
plot_waves(class_audios, raw_audios)
plot_specgram(class_audios, raw_audios)
plot_log_power_specgram(class_audios, raw_audios)

# %%
# check data distribution of training set
dist = train.Class.value_counts()
plt.figure(figsize=(8, 4))
plt.xticks(rotation=60)
plt.bar(dist.index, dist.values)
# %%

files_in_error = []

# Extracts audio features from data
def extract_features(row):
    # function to load files and extract features
    file_name = os.path.join(os.path.abspath('./data/'), DATA_PATH, str(row.ID) + '.wav')

    # handle exception to check if there isn't a file which is corrupted
    try:
        # here kaiser_fast is a technique used for faster extraction
        X, sample_rate = librosa.load(file_name, res_type='kaiser_fast')

        stft = np.abs(librosa.stft(X))

        mfccs = np.mean(librosa.feature.mfcc(y=X, sr=sample_rate, n_mfcc=64).T, axis=0)
        chroma = np.mean(librosa.feature.chroma_stft(S=stft, sr=sample_rate).T, axis=0)
        mel = np.mean(librosa.feature.melspectrogram(X, sr=sample_rate).T, axis=0)
        tonnetz = np.mean(librosa.feature.tonnetz(y=librosa.effects.harmonic(X),
                                                  sr=sample_rate).T, axis=0)
        contrast = np.mean(librosa.feature.spectral_contrast(S=stft, sr=sample_rate).T, axis=0)

    except Exception as e:
        print(file_name, e)
        files_in_error.append(file_name)
        return None

    features = np.hstack([mfccs, chroma, mel, tonnetz, contrast])

    return features

# %%
def dump_features(features, features_filename):
    features = np.vstack(features)
    np.savetxt(features_filename, features, delimiter=",")

# %%
features_train_file = Path("./features_train.csv")

if not features_train_file.is_file():
    features = train.apply(extract_features, axis=1)
    dump_features(features, features_train_file)
    train = train.assign(features=features.values)
else:
    features = pd.read_csv('./features_train.csv', header=None)
    train = train.assign(features=features.values)

# %%

y = np.array(train.loc[:, 'Class'])
X = np.array(train.loc[:, 'features'])

lb = LabelEncoder()

y = np_utils.to_categorical(lb.fit_transform(y))

# %%
num_labels = y.shape[1]

# build model
model = Sequential()

# Input layer
model.add(Dense(256, input_shape=(217,)))
model.add(Activation('relu'))
model.add(Dropout(0.5))

# Hidden layer
model.add(Dense(256))
model.add(Activation('relu'))
model.add(Dropout(0.5))

# Output layer
model.add(Dense(num_labels))
model.add(Activation('softmax'))

# Compile model
model.compile(loss='categorical_crossentropy', metrics=['accuracy'], optimizer='adam')

# %%
X.shape, y.shape

SVG(model_to_dot(model, show_shapes=True, show_layer_names=True).create(prog='dot', format='svg'))

X = np.vstack(X)

X.shape, y.shape

model.fit(X, y, batch_size=32, epochs=50, validation_split=0.20)

# %%

# data directory and csv file should have the same name
DATA_PATH = 'test'

test = pd.read_csv('./data/' + DATA_PATH + '.csv')

features_test_file = Path("./features_test.csv")

if not features_test_file.is_file():
    features = test.apply(extract_features, axis=1)
    dump_features(features, features_test_file)
    test = test.assign(features=features.values)
else:
    features = pd.read_csv('./features_test.csv')
    test = test.assign(features=features.values)

# %%
X_test = np.array(test.loc[:, 'features'])
X_test = np.vstack(X_test)

X_test.shape

# calculate predictions
predictions = model.predict_classes(X_test)
predict_class = lb.inverse_transform(predictions)

test['Class'] = predict_class
test_output = test.copy()

# drop the 'feature' column as it is not required for submission
test_output = test_output.drop(columns=['features'], axis=1)

test_output.to_csv('sub01.csv', index=False)