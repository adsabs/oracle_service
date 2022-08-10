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

    model_file = '/keras_model_files/4layer4dim.pkl'

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
        return float('%.7g' % (np.float32(np.take(self.model.predict([scores]), 0)).item()))

    def save(self):
        """
        save object to a pickle file

        """
        try:
            with open(os.path.dirname(__file__) + self.model_file, "wb") as f:
                pickler = pickle.Pickler(f, -1)
                pickler.dump(self.model)
                # pickler.dump(self.history)
                # pickler.dump(self.test_loss)
                # pickler.dump(self.test_accuracy)
            current_app.logger.info("saved keras model in %s."%self.model_file)
            return True
        except Exception as e:
            current_app.logger.error('Exception: %s' % (str(e)))
            current_app.logger.error(traceback.format_exc())
            return False

    def load(self):
        """

        :return:
        """
        try:
            with open(os.path.dirname(__file__) + self.model_file, "rb") as f:
                unpickler = pickle.Unpickler(f)
                self.model = unpickler.load()
                # self.history = unpickler.load()
                # self.test_loss = unpickler.load()
                # self.test_accuracy = unpickler.load()
            current_app.logger.info("loaded keras model from %s."%self.model_file)
            return self
        except Exception as e:
            current_app.logger.error('Exception: %s' % (str(e)))
            current_app.logger.error(traceback.format_exc())


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

def load_keras_model():
    """
    load the text model from pickle file

    :return:
    """
    try:
        start_time = time.time()
        keras_model = KerasModel()
        if not (keras_model.load()):
            raise
        current_app.logger.debug("keras model loaded in %s ms" % ((time.time() - start_time) * 1000))
        return keras_model
    except Exception as e:
        current_app.logger.error('Exception: %s' % (str(e)))
        current_app.logger.error(traceback.format_exc())
        return None


if __name__ == '__main__':      # pragma: no cover
    PROJECT_HOME = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
    sys.path.append(PROJECT_HOME)
    import oraclesrv.app as app
    current_app = app.create_app()

    parser = argparse.ArgumentParser(description='Build/Save or Load Keras Model')
    parser.add_argument('-a', '--action', help='action to take Create or Load the model')
    args = parser.parse_args()
    if args.action:
        if args.action == 'Create':
            create_keras_model()
        elif args.action == 'Load':
            keras_model = load_keras_model()
            df = pd.DataFrame(columns=['abstract', 'title', 'author', 'year'])
            datapoints = [[1.0, 0.98, 1, 1], [0.76, 0.98, 1, 1]]
            for abstract, title, author, year in datapoints:
                df = df.append({'abstract': abstract, 'title': title, 'author': author, 'year': year},
                               ignore_index=True)
            print(keras_model.model.predict(df))
        else:
            sys.exit(1)
    sys.exit(0)
