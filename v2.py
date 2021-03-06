#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun May  5 17:24:13 2019

@author: thanh
"""

from __future__ import absolute_import, division, print_function

# Import TensorFlow >= 1.10 and enable eager execution
import tensorflow as tf

tf.enable_eager_execution()

import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split

import unicodedata
import re
import numpy as np
import os
import time

import codecs
import csv
import re
import sys

print(tf.__version__)

# Download the file
#path_to_zip = tf.keras.utils.get_file(
#    'spa-eng.zip', origin='http://download.tensorflow.org/data/spa-eng.zip', 
#    extract=True)

path_to_file = "./data/all_4.txt"
#path_to_file = "./data/demo_no_tone_all.txt"

# Converts the unicode file to ascii
def unicode_to_ascii(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s)
        if unicodedata.category(c) != 'Mn')


def preprocess_sentence(w):
    w = w.lower().strip()
    
    # creating a space between a word and the punctuation following it
    # eg: "he is a boy." => "he is a boy ." 
    # Reference:- https://stackoverflow.com/questions/3645931/python-padding-punctuation-with-white-spaces-keeping-punctuation
    w = re.sub(r"([?.!,:])", r" \1 ", w)
    w = re.sub(r'[" "]+', " ", w)
    
    # replacing everything with space except (a-z, A-Z, ".", "?", "!", ",")
    # w = re.sub(r"[^a-zA-Z?.!,¿]+", " ", w)
    
    w = w.rstrip().strip()
    
    # adding a start and an end token to the sentence
    # so that the model know when to start and stop predicting.
    w = '<start> ' + w + ' <end>'
    return w


# 1. Remove the accents
# 2. Clean the sentences
# 3. Return word pairs in the format: [ENGLISH, SPANISH]
def create_dataset(path, num_examples):
    lines = open(path, encoding='UTF-8').read().strip().split('\n')
    
    word_pairs = [[preprocess_sentence(w) for w in l.split('\t')]  for l in lines[:num_examples]]
    
    return word_pairs

# This class creates a word -> index mapping (e.g,. "dad" -> 5) and vice-versa 
# (e.g., 5 -> "dad") for each language,
class LanguageIndex():
  def __init__(self, lang):
    self.lang = lang
    self.word2idx = {}
    self.idx2word = {}
    self.vocab = set()
    
    self.create_index()
    
  def __iter__(self):
    return self
    
  def create_index(self):
    for phrase in self.lang:
      self.vocab.update(phrase.split(' '))
    
    self.vocab = sorted(self.vocab)
    
    self.word2idx['<pad>'] = 0
    for index, word in enumerate(self.vocab):
      self.word2idx[word] = index + 1
    
    for word, index in self.word2idx.items():
      self.idx2word[index] = word
      
def max_length(tensor):
    return max(len(t) for t in tensor)


def load_dataset(path, num_examples):
    # creating cleaned input, output pairs
    pairs = create_dataset(path, num_examples)

    # index language using the class defined above    
    inp_lang = LanguageIndex(sp for en, sp in pairs)
    targ_lang = LanguageIndex(en for en, sp in pairs)
    
    # Vectorize the input and target languages
    
    # Spanish sentences
    input_tensor = [[inp_lang.word2idx[s] for s in sp.split(' ')] for en, sp in pairs]
    
    # English sentences
    target_tensor = [[targ_lang.word2idx[s] for s in en.split(' ')] for en, sp in pairs]
    
    # Calculate max_length of input and output tensor
    # Here, we'll set those to the longest sentence in the dataset
    max_length_inp, max_length_tar = max_length(input_tensor), max_length(target_tensor)
    
    # Padding the input and output tensor to the maximum length
    input_tensor = tf.keras.preprocessing.sequence.pad_sequences(input_tensor, 
                                                                 maxlen=max_length_inp,
                                                                 padding='post')
    
    target_tensor = tf.keras.preprocessing.sequence.pad_sequences(target_tensor, 
                                                                  maxlen=max_length_tar, 
                                                                  padding='post')
    
    return input_tensor, target_tensor, inp_lang, targ_lang, max_length_inp, max_length_tar

# Try experimenting with the size of that dataset
num_examples = 1000000
input_tensor, target_tensor, inp_lang, targ_lang, max_length_inp, max_length_targ = load_dataset(path_to_file, num_examples)


# Creating training and validation sets using an 80-20 split
input_tensor_train, input_tensor_val, target_tensor_train, target_tensor_val = train_test_split(input_tensor, target_tensor, test_size=0.2)

# Show length
print (len(input_tensor_train), len(target_tensor_train), len(input_tensor_val), len(target_tensor_val), max_length_inp, max_length_targ)

BUFFER_SIZE = len(input_tensor_train)
BATCH_SIZE = 256
N_BATCH = BUFFER_SIZE//BATCH_SIZE
embedding_dim = 256
units = 768
vocab_inp_size = len(inp_lang.word2idx)
vocab_tar_size = len(targ_lang.word2idx)

dataset = tf.data.Dataset.from_tensor_slices((input_tensor_train, target_tensor_train)).shuffle(BUFFER_SIZE)
dataset = dataset.batch(BATCH_SIZE, drop_remainder=True)

def gru(units):
  # If you have a GPU, we recommend using CuDNNGRU(provides a 3x speedup than GRU)
  # the code automatically does that.
  if tf.test.is_gpu_available():
    return tf.keras.layers.CuDNNGRU(units, 
                                    return_sequences=True, 
                                    return_state=True, 
                                    recurrent_initializer='glorot_uniform')
  else:
    return tf.keras.layers.GRU(units, 
                               return_sequences=True, 
                               return_state=True, 
                               recurrent_activation='sigmoid', 
                               recurrent_initializer='glorot_uniform')
    
class Encoder(tf.keras.Model):
    def __init__(self, vocab_size, embedding_dim, enc_units, batch_sz):
        super(Encoder, self).__init__()
        self.batch_sz = batch_sz
        self.enc_units = enc_units
        self.embedding = tf.keras.layers.Embedding(vocab_size, embedding_dim)
        self.gru = gru(self.enc_units)
        
    def call(self, x, hidden):
        x = self.embedding(x)
        output, state = self.gru(x, initial_state = hidden)        
        return output, state
    
    def initialize_hidden_state(self):
        return tf.zeros((self.batch_sz, self.enc_units))
    
class Decoder(tf.keras.Model):
    def __init__(self, vocab_size, embedding_dim, dec_units, batch_sz):
        super(Decoder, self).__init__()
        self.batch_sz = batch_sz
        self.dec_units = dec_units
        self.embedding = tf.keras.layers.Embedding(vocab_size, embedding_dim)
        self.gru = gru(self.dec_units)
        self.fc = tf.keras.layers.Dense(vocab_size)
        
        # used for attention
        self.W1 = tf.keras.layers.Dense(self.dec_units)
        self.W2 = tf.keras.layers.Dense(self.dec_units)
        self.V = tf.keras.layers.Dense(1)
        
    def call(self, x, hidden, enc_output):
        # enc_output shape == (batch_size, max_length, hidden_size)
        
        # hidden shape == (batch_size, hidden size)
        # hidden_with_time_axis shape == (batch_size, 1, hidden size)
        # we are doing this to perform addition to calculate the score
        hidden_with_time_axis = tf.expand_dims(hidden, 1)
        
        # score shape == (batch_size, max_length, 1)
        # we get 1 at the last axis because we are applying tanh(FC(EO) + FC(H)) to self.V
        score = self.V(tf.nn.tanh(self.W1(enc_output) + self.W2(hidden_with_time_axis)))
        
        # attention_weights shape == (batch_size, max_length, 1)
        attention_weights = tf.nn.softmax(score, axis=1)
        
        # context_vector shape after sum == (batch_size, hidden_size)
        context_vector = attention_weights * enc_output
        context_vector = tf.reduce_sum(context_vector, axis=1)
        
        # x shape after passing through embedding == (batch_size, 1, embedding_dim)
        x = self.embedding(x)
        
        # x shape after concatenation == (batch_size, 1, embedding_dim + hidden_size)
        x = tf.concat([tf.expand_dims(context_vector, 1), x], axis=-1)
        
        # passing the concatenated vector to the GRU
        output, state = self.gru(x)
        
        # output shape == (batch_size * 1, hidden_size)
        output = tf.reshape(output, (-1, output.shape[2]))
        
        # output shape == (batch_size * 1, vocab)
        x = self.fc(output)
        
        return x, state, attention_weights
        
    def initialize_hidden_state(self):
        return tf.zeros((self.batch_sz, self.dec_units))

encoder = Encoder(vocab_inp_size, embedding_dim, units, BATCH_SIZE)
decoder = Decoder(vocab_tar_size, embedding_dim, units, BATCH_SIZE)

optimizer = tf.train.AdamOptimizer()


def loss_function(real, pred):
  mask = 1 - np.equal(real, 0)
  loss_ = tf.nn.sparse_softmax_cross_entropy_with_logits(labels=real, logits=pred) * mask
  return tf.reduce_mean(loss_)

checkpoint_dir = './training_checkpoints'
checkpoint_prefix = os.path.join(checkpoint_dir, "ckpt")
checkpoint = tf.train.Checkpoint(optimizer=optimizer,
                                 encoder=encoder,
                                 decoder=decoder)

checkpoint_dir = './training_checkpoints'
checkpoint_prefix = os.path.join(checkpoint_dir, "ckpt")
checkpoint = tf.train.Checkpoint(optimizer=optimizer,
                                 encoder=encoder,
                                 decoder=decoder)

def training(BEGIN=0, EPOCHS = 20):
    
    
    for epoch in range(BEGIN,EPOCHS):
        start = time.time()
        
        hidden = encoder.initialize_hidden_state()
        total_loss = 0
        
        for (batch, (inp, targ)) in enumerate(dataset):
            loss = 0
            
            with tf.GradientTape() as tape:
                enc_output, enc_hidden = encoder(inp, hidden)
                
                dec_hidden = enc_hidden
                
                dec_input = tf.expand_dims([targ_lang.word2idx['<start>']] * BATCH_SIZE, 1)       
                
                # Teacher forcing - feeding the target as the next input
                for t in range(1, targ.shape[1]):
                    # passing enc_output to the decoder
                    predictions, dec_hidden, _ = decoder(dec_input, dec_hidden, enc_output)
                    
                    loss += loss_function(targ[:, t], predictions)
                    
                    # using teacher forcing
                    dec_input = tf.expand_dims(targ[:, t], 1)
            
            batch_loss = (loss / int(targ.shape[1]))
            
            total_loss += batch_loss
            
            variables = encoder.variables + decoder.variables
            
            gradients = tape.gradient(loss, variables)
            
            optimizer.apply_gradients(zip(gradients, variables))
            
            if batch % 100 == 0:
                print('Epoch {} Batch {} Loss {:.4f}'.format(epoch + 1,
                                                             batch,
                                                             batch_loss.numpy()))
        # saving (checkpoint) the model every 2 epochs
        if (epoch + 1) % 2 == 0:
          checkpoint.save(file_prefix = checkpoint_prefix)
        
        print('Epoch {} Loss {:.4f}'.format(epoch + 1,
                                            total_loss / N_BATCH))
        print('Time taken for 1 epoch {} sec\n'.format(time.time() - start))
        test()
    
def evaluate(sentence, encoder, decoder, inp_lang, targ_lang, max_length_inp, max_length_targ):
    attention_plot = np.zeros((max_length_targ, max_length_inp))
    
    sentence = preprocess_sentence(sentence)

    inputs = [inp_lang.word2idx[i] for i in sentence.split(' ')]
    inputs = tf.keras.preprocessing.sequence.pad_sequences([inputs], maxlen=max_length_inp, padding='post')
    inputs = tf.convert_to_tensor(inputs)
    
    result = ''

    hidden = [tf.zeros((1, units))]
    enc_out, enc_hidden = encoder(inputs, hidden)

    dec_hidden = enc_hidden
    dec_input = tf.expand_dims([targ_lang.word2idx['<start>']], 0)

    for t in range(max_length_targ):
        predictions, dec_hidden, attention_weights = decoder(dec_input, dec_hidden, enc_out)
        
        # storing the attention weigths to plot later on
        attention_weights = tf.reshape(attention_weights, (-1, ))
        attention_plot[t] = attention_weights.numpy()

        predicted_id = tf.argmax(predictions[0]).numpy()

        result += targ_lang.idx2word[predicted_id] + ' '

        if targ_lang.idx2word[predicted_id] == '<end>':
            return result, sentence, attention_plot
        
        # the predicted ID is fed back into the model
        dec_input = tf.expand_dims([predicted_id], 0)

    return result, sentence, attention_plot


# function for plotting the attention weights
def plot_attention(attention, sentence, predicted_sentence):
    fig = plt.figure(figsize=(10,10))
    ax = fig.add_subplot(1, 1, 1)
    ax.matshow(attention, cmap='viridis')
    
    fontdict = {'fontsize': 14}
    
    ax.set_xticklabels([''] + sentence, fontdict=fontdict, rotation=90)
    ax.set_yticklabels([''] + predicted_sentence, fontdict=fontdict)

    plt.show()
    
def remove_tone_line(utf8_str):
    intab_l = "ạảãàáâậầấẩẫăắằặẳẵóòọõỏôộổỗồốơờớợởỡéèẻẹẽêếềệểễúùụủũưựữửừứíìịỉĩýỳỷỵỹđ"
    intab_u = "ẠẢÃÀÁÂẬẦẤẨẪĂẮẰẶẲẴÓÒỌÕỎÔỘỔỖỒỐƠỜỚỢỞỠÉÈẺẸẼÊẾỀỆỂỄÚÙỤỦŨƯỰỮỬỪỨÍÌỊỈĨÝỲỶỴỸĐ"
    intab = intab_l+intab_u

    outtab_l = "a"*17 + "o"*17 + "e"*11 + "u"*11 + "i"*5 + "y"*5 + "d"
    outtab_u = "A"*17 + "O"*17 + "E"*11 + "U"*11 + "I"*5 + "Y"*5 + "D"
    outtab = outtab_l + outtab_u

    r = re.compile("|".join(intab))
    replaces_dict = dict(zip(intab, outtab))

    return r.sub(lambda m: replaces_dict[m.group(0)], utf8_str)

def translate(sentence, encoder, decoder, inp_lang, targ_lang, max_length_inp, max_length_targ):
    try:
        result, sentence, attention_plot = evaluate(sentence, encoder, decoder, inp_lang, targ_lang, max_length_inp, max_length_targ)
    except KeyError as e:
        miss =str(e)[1:-1]
        sentence = sentence.lower()
        try_line = sentence.split(miss)
        # print(sentence, try_line)
        result_line = miss.join(" "+translate(x, encoder, decoder, inp_lang, targ_lang, max_length_inp, max_length_targ)+" " for x in try_line)
        return result_line
    # print('Input: {}'.format(sentence))
    # print('Predicted translation: {}'.format(result))
    
    # attention_plot = attention_plot[:len(result.split(' ')), :len(sentence.split(' '))]
    # plot_attention(attention_plot, sentence.split(' '), result.split(' '))
    
    # fix false 
    sentence = sentence.replace("<end>","").replace("<start>","").strip()
    result = result.replace("<end>","").strip()
    # print(sentence, result)
    false_num = len(sentence.split(" ")) - len(result.split(" "))
    if false_num  < 0:
        max_len = len(sentence.split(" "))
        result = " ".join(result.split(" ")[:max_len])
    elif false_num > 0:
        for i in range(false_num):
            result = result + " f" 
            
    sen_word = sentence.strip().split(" ")
    result_w = result.strip().split(" ")
    for i in range(len(sen_word)):
        if remove_tone_line(result_w[i]) != sen_word[i]:
            # print(remove_tone_line(result_w[i]) +" "+ sen_word[i],"----")
            result_w[i] = sen_word[i]
    
    return " ".join(result_w)

        
    
def test():
    translate(u'toi la toi', encoder, decoder, inp_lang, targ_lang, max_length_inp, max_length_targ)
    translate(u'Trung Quoc da mo rong anh huong cua ho trong khu vuc thong qua cac buoc leo thang ep buoc cac nuoc lang gieng', encoder, decoder, inp_lang, targ_lang, max_length_inp, max_length_targ)
    translate(u'Tai ho so vu an', encoder, decoder, inp_lang, targ_lang, max_length_inp, max_length_targ)
    translate(u'Trong nhung nam qua', encoder, decoder, inp_lang, targ_lang, max_length_inp, max_length_targ)
    translate(u'anh yeu em', encoder, decoder, inp_lang, targ_lang, max_length_inp, max_length_targ)
    translate(u'Truoc su phan ung cua cac nha xe hoat dong hop phap', encoder, decoder, inp_lang, targ_lang, max_length_inp, max_length_targ)
    translate(u'ngay xua co mot con bo', encoder, decoder, inp_lang, targ_lang, max_length_inp, max_length_targ)
    translate(u'chu nghia xa hoi', encoder, decoder, inp_lang, targ_lang, max_length_inp, max_length_targ)
    translate(u'the gioi phang', encoder, decoder, inp_lang, targ_lang, max_length_inp, max_length_targ)
    translate(u'lien hoan phim', encoder, decoder, inp_lang, targ_lang, max_length_inp, max_length_targ)
    translate(u'chien tranh va hoa binh', encoder, decoder, inp_lang, targ_lang, max_length_inp, max_length_targ)
        
def tran(sen):
    word = sen.split()
    line=""
    for i in range(0,len(word),4):
        line=line +" "+ translate(" ".join(word[i:i+4]), encoder, decoder, inp_lang, targ_lang, max_length_inp, max_length_targ).strip()
        
    # print(line)
    return line

# restoring the latest checkpoint in checkpoint_dir
checkpoint.restore(tf.train.latest_checkpoint(checkpoint_dir))

#training(1,60)

#checkpoint.restore(tf.train.latest_checkpoint("temp"))
translate(u'lien hoan phim', encoder, decoder, inp_lang, targ_lang, max_length_inp, max_length_targ)

def add_tone_file(in_path, out_path):
    with codecs.open(in_path, 'r', encoding='utf-8') as in_file,\
            codecs.open(out_path, 'w', encoding='utf-8') as out_file:
        for line in in_file:
            utf8_line = line.encode('utf-8')
            # print(utf8_line[4:])
            # no_tone_line = remove_tone_line(utf8_line)
            #no_tone_sen = re.split(';|:|,|\.',no_tone_line)
            utf8_sen = re.split(';|:|\?|,|\.',utf8_line[4:].decode('utf-8'))
            print(utf8_sen)
            decode_line = "".join(tran(w) for w in utf8_sen)
            print(decode_line)
            print(utf8_line[0:4])
            try:
                out_file.write(utf8_line[0:4].decode('utf-8')+decode_line+"\n")
            except UnicodeDecodeError as e:
                    print ('Line with decode error:')
                    print (e)

add_tone_file("./data/test.txt","./data/5.txt")