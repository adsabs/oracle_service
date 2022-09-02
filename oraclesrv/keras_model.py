import os, sys
import traceback
import time
import argparse

import pandas as pd
import numpy as np
from tensorflow import keras
from tensorflow.keras import layers
from sklearn.model_selection import train_test_split

from flask import current_app

try:
    import cPickle as pickle
except ImportError:
    import pickle


class KerasModel(object):

    training_file = '/keras_model_files/data.csv'

    units = [16, 16, 8, 8, 1]
    optimizer = 'adam'
    loss = 'binary_crossentropy'
    epoch = 100
    batch_size = 1

    model_file = os.path.dirname(__file__) + '/keras_model_files/4layer4dim'

    model_loaded = False

    def train(self):
        """

        :return:
        """

        df = pd.read_csv(os.path.dirname(__file__) + self.training_file)
        properties = list(df.columns.values)
        properties.remove('label')
        X = df[properties]
        y = df['label']

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=0)
        len_test_valid = len(y_test)
        x_val = X_train[:len_test_valid]
        partial_x_train = X_train[len_test_valid:]
        y_val = y_train[:len_test_valid]
        partial_y_train = y_train[len_test_valid:]

        width = X_train.shape[1]
        self.model = keras.Sequential([
            layers.Flatten(input_shape=(width,)),
            layers.Dense(self.units[0], activation="relu"),
            layers.Dense(self.units[1], activation="relu"),
            layers.Dense(self.units[2], activation="relu"),
            layers.Dense(self.units[3], activation="relu"),
            layers.Dense(1, activation="sigmoid"),
        ])

        self.model.compile(optimizer=self.optimizer,
                      loss=self.loss,
                      metrics=['accuracy'])

        self.history = self.model.fit(partial_x_train,
                            partial_y_train,
                            epochs=self.epoch,
                            batch_size=self.batch_size,
                            validation_data=(x_val, y_val),
                            verbose=0)

        self.test_loss, self.test_accuracy = self.model.evaluate(X_test, y_test)

        return (self.test_accuracy >= 0.95)

    def predict(self, scores):
        """

        :param scores: list of scores for [abstract, title, author, year]
        :return:
        """
        try:
            if not self.model_loaded:
                self.load()
                self.model_loaded = True
            current_app.logger.debug("Predict score ...")
            start_time = time.time()
            prediction_score = self.model.predict([scores])[0][0].item()
            current_app.logger.debug("Predict score took {duration} ms".format(duration=(time.time() - start_time) * 1000))
            confidence_format = '%.{}f'.format(current_app.config['ORACLE_SERVICE_CONFIDENCE_SIGNIFICANT_DIGITS'])
            return float(confidence_format % prediction_score)
        except Exception as e:
            current_app.logger.error(str(e))
            return 0

    def save(self):
        """
        save model

        """
        self.model.save(self.model_file)

    def load(self):
        """

        :return:
        """
        start_time = time.time()
        self.model = keras.models.load_model(self.model_file)
        current_app.logger.debug("Loading model took {duration} ms".format(duration=(time.time() - start_time) * 1000))


def create_keras_model():
    """
    create a crf text model and save it to a pickle file

    :return:
    """
    try:
        start_time = time.time()
        keras_model = KerasModel()
        if not (keras_model.train() and keras_model.save()):
            raise
        current_app.logger.debug("crf text model trained and saved in %s ms" % ((time.time() - start_time) * 1000))
        return keras_model
    except Exception as e:
        current_app.logger.error('Exception: %s' % (str(e)))
        current_app.logger.error(traceback.format_exc())
        return None
