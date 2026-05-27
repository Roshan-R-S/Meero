import pickle, json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import config

def main():
    with open('models/label_encoder.pkl','rb') as f:
        le = pickle.load(f)
    with open('models/tokenizer.pkl','rb') as f:
        tk = pickle.load(f)
    meta = None
    try:
        with open('models/chat_model.h5.metadata.json','r',encoding='utf-8') as f:
            meta = json.load(f)
    except FileNotFoundError:
        pass

    print('label_classes=', getattr(le, 'classes_', None))
    print('tokenizer_num_words=', getattr(tk, 'num_words', None))
    print('tokenizer_word_index_len=', len(getattr(tk, 'word_index', {})))
    print('metadata=', meta)

if __name__=='__main__':
    main()
