import os, sys
import traceback
import time
import argparse

import pandas as pd
from tensorflow import keras
from tensorflow.keras import layers
from sklearn.model_selection import train_test_split

from flask import current_app

try:
    import cPickle as pickle
except ImportError:
    import pickle


class KerasModel(object):

    # abstract/title/author/year
    training_file_4dim = '/keras_model_files/data_4dim.csv'
    # no abstract
    training_file_3dim = '/keras_model_files/data_3dim.csv'
    # abstract/title/author/year/doi
    training_file_4dim_w_doi = '/keras_model_files/data_4dim_w_doi.csv'
    # no abstract but with doi
    training_file_3dim_w_doi = '/keras_model_files/data_3dim_w_doi.csv'

    units_4dim = [16, 16, 8, 8, 1]
    units_3dim = [16, 8, 8, 1]
    units_4dim_w_doi = [16, 16, 8, 8, 8, 1]
    units_3dim_w_doi = [16, 8, 8, 8, 1]

    optimizer = 'adam'
    loss = 'binary_crossentropy'
    epoch = 100
    batch_size = 1

    model_file_4dim = os.path.dirname(__file__) + '/keras_model_files/4layer4dim'
    model_file_3dim = os.path.dirname(__file__) + '/keras_model_files/3layer3dim'
    model_file_4dim_w_doi = os.path.dirname(__file__) + '/keras_model_files/5layer4dim_w_doi'
    model_file_3dim_w_doi = os.path.dirname(__file__) + '/keras_model_files/4layer3dim_w_doi'

    model_loaded = False

    def train_data_4dim(self): # pragma: no cover
        """
        train a model for having abstract/title/author/year

        :return:
        """

        df = pd.read_csv(os.path.dirname(__file__) + self.training_file_4dim)
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
        self.model_4dim = keras.Sequential([
            layers.Flatten(input_shape=(width,)),
            layers.Dense(self.units_4dim[0], activation="relu"),
            layers.Dense(self.units_4dim[1], activation="relu"),
            layers.Dense(self.units_4dim[2], activation="relu"),
            layers.Dense(self.units_4dim[3], activation="relu"),
            layers.Dense(1, activation="sigmoid"),
        ])

        self.model_4dim.compile(optimizer=self.optimizer,
                      loss=self.loss,
                      metrics=['accuracy'])

        self.history = self.model_4dim.fit(partial_x_train,
                            partial_y_train,
                            epochs=self.epoch,
                            batch_size=self.batch_size,
                            validation_data=(x_val, y_val),
                            verbose=0)

        self.test_loss, self.test_accuracy = self.model_4dim.evaluate(X_test, y_test)

        return (self.test_accuracy >= 0.95)

    def train_data_3dim(self): # pragma: no cover
        """
        train a model for having title/author/year

        :return:
        """

        df = pd.read_csv(os.path.dirname(__file__) + self.training_file_3dim)
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
        self.model_3dim = keras.Sequential([
            layers.Flatten(input_shape=(width,)),
            layers.Dense(self.units_3dim[0], activation="relu"),
            layers.Dense(self.units_3dim[1], activation="relu"),
            layers.Dense(self.units_3dim[2], activation="relu"),
            layers.Dense(1, activation="sigmoid"),
        ])

        self.model_3dim.compile(optimizer=self.optimizer,
                      loss=self.loss,
                      metrics=['accuracy'])

        self.history = self.model_3dim.fit(partial_x_train,
                            partial_y_train,
                            epochs=self.epoch,
                            batch_size=self.batch_size,
                            validation_data=(x_val, y_val),
                            verbose=0)

        self.test_loss, self.test_accuracy = self.model_3dim.evaluate(X_test, y_test)

        return (self.test_accuracy >= 0.95)

    def train_data_4dim_w_doi(self): # pragma: no cover
        """
        train a model for having abstract/title/author/year/doi

        :return:
        """

        df = pd.read_csv(os.path.dirname(__file__) + self.training_file_4dim_w_doi)
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
        self.model_4dim_w_doi = keras.Sequential([
            layers.Flatten(input_shape=(width,)),
            layers.Dense(self.units_4dim_w_doi[0], activation="relu"),
            layers.Dense(self.units_4dim_w_doi[1], activation="relu"),
            layers.Dense(self.units_4dim_w_doi[2], activation="relu"),
            layers.Dense(self.units_4dim_w_doi[3], activation="relu"),
            layers.Dense(self.units_4dim_w_doi[4], activation="relu"),
            layers.Dense(1, activation="sigmoid"),
        ])

        self.model_4dim_w_doi.compile(optimizer=self.optimizer,
                      loss=self.loss,
                      metrics=['accuracy'])

        self.history = self.model_4dim_w_doi.fit(partial_x_train,
                            partial_y_train,
                            epochs=self.epoch,
                            batch_size=self.batch_size,
                            validation_data=(x_val, y_val),
                            verbose=0)

        self.test_loss, self.test_accuracy = self.model_4dim_w_doi.evaluate(X_test, y_test)

        return (self.test_accuracy >= 0.95)

    def train_data_3dim_w_doi(self): # pragma: no cover
        """
        train a model for having title/author/year/doi

        :return:
        """

        df = pd.read_csv(os.path.dirname(__file__) + self.training_file_3dim_w_doi)
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
        self.model_3dim_w_doi = keras.Sequential([
            layers.Flatten(input_shape=(width,)),
            layers.Dense(self.units_3dim_w_doi[0], activation="relu"),
            layers.Dense(self.units_3dim_w_doi[1], activation="relu"),
            layers.Dense(self.units_3dim_w_doi[2], activation="relu"),
            layers.Dense(self.units_3dim_w_doi[3], activation="relu"),
            layers.Dense(1, activation="sigmoid"),
        ])

        self.model_3dim_w_doi.compile(optimizer=self.optimizer,
                      loss=self.loss,
                      metrics=['accuracy'])

        self.history = self.model_3dim_w_doi.fit(partial_x_train,
                            partial_y_train,
                            epochs=self.epoch,
                            batch_size=self.batch_size,
                            validation_data=(x_val, y_val),
                            verbose=0)

        self.test_loss, self.test_accuracy = self.model_3dim_w_doi.evaluate(X_test, y_test)

        return (self.test_accuracy >= 0.95)

    def train(self): # pragma: no cover
        """

        :return:
        """
        return self.train_data_4dim() and self.train_data_3dim() and \
               self.train_data_4dim_w_doi() and self.train_data_3dim_w_doi()

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
            # no doi
            if len(scores) == 4:
                if scores[0] != None:
                    # with abstract
                    prediction_score = self.model_4dim.predict([scores])[0][0].item()
                else:
                    # no abstract
                    prediction_score = self.model_3dim.predict([scores[1:]])[0][0].item()
            # with addition of doi
            elif len(scores) == 5:
                if scores[0] != None:
                    # with abstract
                    prediction_score = self.model_4dim_w_doi.predict([scores])[0][0].item()
                else:
                    # no abstract
                    prediction_score = self.model_3dim_w_doi.predict([scores[1:]])[0][0].item()
            else:
                current_app.logger.error('Unable to predict score, wrong dimension %d received!'%len(scores))
                return 0
            current_app.logger.debug("Predict score took {duration} ms".format(duration=(time.time() - start_time) * 1000))
            confidence_format = '%.{}f'.format(current_app.config['ORACLE_SERVICE_CONFIDENCE_SIGNIFICANT_DIGITS'])
            return float(confidence_format % prediction_score)
        except Exception as e:
            current_app.logger.error(str(e))
            return 0

    def save(self): # pragma: no cover
        """
        save model

        """
        self.model_4dim.save(self.model_file_4dim)
        self.model_3dim.save(self.model_file_3dim)
        self.model_4dim_w_doi.save(self.model_file_4dim_w_doi)
        self.model_3dim_w_doi.save(self.model_file_3dim_w_doi)

    def load(self): # pragma: no cover
        """

        :return:
        """
        start_time = time.time()
        self.model_4dim = keras.models.load_model(self.model_file_4dim)
        self.model_3dim = keras.models.load_model(self.model_file_3dim)
        self.model_4dim_w_doi = keras.models.load_model(self.model_file_4dim_w_doi)
        self.model_3dim_w_doi = keras.models.load_model(self.model_file_3dim_w_doi)
        current_app.logger.debug("Loading model took {duration} ms".format(duration=(time.time() - start_time) * 1000))


def create_keras_model():  # pragma: no cover
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
