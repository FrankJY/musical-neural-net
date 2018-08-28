from fastai.learner import *
import torchtext
from torchtext import vocab, data
from torchtext.datasets import language_modeling
from fastai.rnn_reg import *
from fastai.rnn_train import *
from fastai.nlp import *
from fastai.lm_rnn import *
from utils import *

import dill as pickle
import argparse

PATH = Path('./data/')
OUT = PATH/'models'
TRAIN = 'train'
VALIDATION = 'test'

OUT.mkdir(parents=True, exist_ok=True)

def music_tokenizer(x): return x.split(" ")
    
def main(model_to_load, model_out, bs, bptt, em_sz, nh, nl, min_freq, dropout_multiplier, epochs):
    TEXT = data.Field(lower=True, tokenize=music_tokenizer)
    # Adam Optimizer with slightly lowered momentum 
    optimizer_function = partial(optim.Adam, betas=(0.7, 0.99))  
    FILES = dict(train=TRAIN, validation=VALIDATION, test=VALIDATION)    
    
    # Build a FastAI Language Model Dataset from the training and validation set
    # Mark as <unk> any words not used at least min_freq times
    md = LanguageModelData.from_text_files(PATH, TEXT, **FILES, bs=bs, bptt=bptt, min_freq=min_freq)
    print("Number of tokens: "+str(md.nt))
    
    # Save parameters so that it's fast to rebuild network in generate.py
    dump_param_dict(TEXT, md, bs, bptt, em_sz, nh, nl, model_out)
    
    # AWD LSTM model parameters (with dropout_multiplier=1, these are the values recommended 
    # by the AWD LSTM paper. For notewise encoding, I found that higher amounts of dropout
    # often worked better)
    learner = md.get_model(optimizer_function, em_sz, nh, nl, dropouti=0.05*dropout_multiplier, 
                           dropout=0.05*dropout_multiplier, wdrop=0.1*dropout_multiplier,
                           dropoute=0.02*dropout_multiplier, dropouth=0.05*dropout_multiplier)
    
    learner.reg_fn = partial(seq2seq_reg, alpha=2, beta=1)    # Applying regularization
    learner.clip=0.3                                          # Clip the gradients

    if model_to_load:
        print("Loading: "+model_to_load)
        learner.model.load_state_dict(torch.load(OUT/model_to_load))       

    lrs=[3e-3, 3e-4, 3e-6, 3e-8]
    trainings=["_light.pth", "_med.pth", "_full.pth", "_extra.pth"] 
    save_names=[model_out+b for b in trainings]
    save_names=[OUT/s for s in save_names]
        
    for i in range(len(lrs)):
        train_and_save(learner, lrs[i], epochs, save_names[i])

    
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--bs", dest="bs", help="Batch Size (default 16)", type=int) 
    parser.set_defaults(bs=16)
    parser.add_argument("--bptt", dest="bs", help="Back Prop Through Time (default 200)", type=int) 
    parser.set_defaults(bptt=200)
    parser.add_argument("--em_sz", dest="em_sz", help="Embedding Size (default 400)", type=int) 
    parser.set_defaults(em_sz=400)  
    parser.add_argument("--nh", dest="nh", help="Number of Hidden Activations (default 600)", type=int) 
    parser.set_defaults(nh=600)
    parser.add_argument("--nl", dest="nl", help="Number of LSTM Layers (default 4)", type=int) 
    parser.set_defaults(nl=4)
    parser.add_argument("--min_freq", dest="min_freq", help="Minimum frequencey of word (default 1)", type=int) 
    parser.set_defaults(min_freq=1)  
    parser.add_argument("--epochs", dest="epochs", help="Epochs per training stage (default 3)", type=int) 
    parser.set_defaults(epochs=3)      
    parser.add_argument("--prefix", dest="prefix", help="Prefix for saving model (default mod)") 
    parser.set_defaults(prefix="mod")
    parser.add_argument("--dropout", dest="dropout", help="Dropout multiplier (default: 1, range 0-5.)", type=float) 
    parser.set_defaults(dropout=1)    
    parser.add_argument("--load_model", dest="model_to_load", help="Optional partially trained model state dict")
    args = parser.parse_args()

    main(args.model_to_load,args.prefix, args.bs, args.bptt, args.em_sz, args.nh, args.nl, args.min_freq, args.dropout, args.epochs)