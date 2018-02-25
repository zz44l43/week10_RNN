#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import tensorflow as tf


class Model():
    def __init__(self, learning_rate=0.001, batch_size=16, num_steps=32, num_words=5000, dim_embedding=128, rnn_layers=3):
        self.batch_size = batch_size
        self.num_steps = num_steps
        self.num_words = num_words
        self.dim_embedding = dim_embedding
        self.rnn_layers = rnn_layers
        self.learning_rate = learning_rate

    def build(self, embedding_file=None):
        # global step
        self.global_step = tf.Variable(
            0, trainable=False, name='self.global_step', dtype=tf.int64)

        self.X = tf.placeholder(
            tf.int32, shape=[None, self.num_steps], name='input')
        self.Y = tf.placeholder(
            tf.int32, shape=[None, self.num_steps], name='label')

        self.keep_prob = tf.placeholder(tf.float32, name='self.keep_prob')

        with tf.variable_scope('embedding'):
            if embedding_file:
                # if embedding file provided, use it.
                embedding = np.load(embedding_file)
                embed = tf.constant(embedding, name='embedding')
            else:
                # if not, initialize an embedding and train it.
                embed = tf.get_variable(
                    'embedding', [self.num_words, self.dim_embedding])
                tf.summary.histogram('embed', embed)

            data = tf.nn.embedding_lookup(embed, self.X)

        with tf.variable_scope('rnn'):
            state_size = self.dim_embedding

            def make_cell():
                cell = tf.nn.rnn_cell.BasicLSTMCell(state_size)
                # cell = tf.cond(self.keep_prob < 1, tf.contrib.rnn.DropoutWrapper(cell, output_keep_prob=self.keep_prob), cell)
                # if self.keep_prob < 1:
                #     cell = tf.contrib.rnn.DropoutWrapper(cell, output_keep_prob=self.keep_prob)
                return cell

            outputs_tensor = tf.contrib.rnn.MultiRNNCell([make_cell() for _ in range(self.rnn_layers)])
            self.state_tensor = state = outputs_tensor.zero_state(self.batch_size, tf.float32)
            # seq_output = []
            # for step in range(self.num_steps):
            #     if step > 0: tf.get_variable_scope().reuse_variables()
            #     outputs, state = stacked_lstm(data[:,step, :],state)
            #     seq_output.append(outputs)
            # seq_output = tf.reshape(tf.concat(outputs, 1), [-1, state_size])
        # concate every time step
        seq_output = tf.concat(outputs_tensor, 1)

        # flatten it
        seq_output_final = tf.reshape(seq_output, [-1, self.dim_embedding])
        self.outputs_state_tensor = state
        with tf.variable_scope('softmax'):
            softmax_w = tf.get_variable("softmax_w", [state_size, self.num_words], initializer=tf.random_normal_initializer(stddev=0.01))
            softmax_b = tf.get_variable("softmax_b", [self.num_words], initializer=tf.constant_initializer(0.0))
            logits = tf.reshape(tf.matmul(tf.reshape(seq_output_final, [-1, state_size]), softmax_w) +
                                softmax_b,[self.batch_size, self.num_steps, 5000])

        tf.summary.histogram('logits', logits)

        self.predictions = tf.nn.softmax(logits, name='predictions')

        y_one_hot = tf.one_hot(self.Y, self.num_words)
        y_reshaped = tf.reshape(y_one_hot, logits.get_shape())
        loss = tf.nn.softmax_cross_entropy_with_logits(
            logits=logits, labels=y_reshaped)
        self.loss = tf.reduce_mean(loss)

        # gradient clip
        tvars = tf.trainable_variables()
        grads, _ = tf.clip_by_global_norm(tf.gradients(loss, tvars), 5)
        train_op = tf.train.AdamOptimizer(self.learning_rate)
        self.optimizer = train_op.apply_gradients(
            zip(grads, tvars), global_step=self.global_step)

        tf.summary.scalar('loss', self.loss)

        self.merged_summary_op = tf.summary.merge_all()
