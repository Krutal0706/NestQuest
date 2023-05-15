#pip install streamlit langchain openai faiss-cpu tiktoken streamlit_bokeh_events gtts

import streamlit as st
from streamlit_chat import message
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.chat_models import ChatOpenAI
from langchain.chains import ConversationalRetrievalChain
from langchain.document_loaders.csv_loader import CSVLoader
from langchain.vectorstores import FAISS
import tempfile
import os

from bokeh.models.widgets import Button
from bokeh.models import CustomJS

from streamlit_bokeh_events import streamlit_bokeh_events

from gtts import gTTS
from io import BytesIO
import openai


user_api_key = "API KEY"

os.environ["OPENAI_API_KEY"] = "API KEY"

tmp_file_path = "realestate_fianl_dataset.csv"

loader = CSVLoader(file_path=tmp_file_path, csv_args={
'delimiter': ','
})
data = loader.load()

embeddings = OpenAIEmbeddings()
vectors = FAISS.from_documents(data, embeddings)

chain = ConversationalRetrievalChain.from_llm(llm = ChatOpenAI(temperature=0.0,model_name='gpt-3.5-turbo', openai_api_key=user_api_key), retriever=vectors.as_retriever())

#############################################################################################################
if 'prompts' not in st.session_state:
    st.session_state['prompts'] = [{"role": "system", "content": "You are a helpful assistant. Answer as concisely as possible."}]

def generate_response(prompt):

    st.session_state['prompts'].append({"role": "user", "content":prompt})
    completion=openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages = st.session_state['prompts']
    )
    
    message=completion.choices[0].message.content
    return message

sound = BytesIO()

placeholder = st.container()

placeholder.title("Dr.Tony's Voice ChatBot")
stt_button = Button(label='SPEAK', button_type='success', margin = (5, 5, 5, 5), width=200)

stt_button.js_on_event("button_click", CustomJS(code="""
    var value = "";
    var rand = 0;
    var recognition = new webkitSpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = 'en';

    document.dispatchEvent(new CustomEvent("GET_ONREC", {detail: 'start'}));
    
    recognition.onspeechstart = function () {
        document.dispatchEvent(new CustomEvent("GET_ONREC", {detail: 'running'}));
    }
    recognition.onsoundend = function () {
        document.dispatchEvent(new CustomEvent("GET_ONREC", {detail: 'stop'}));
    }
    recognition.onresult = function (e) {
        var value2 = "";
        for (var i = e.resultIndex; i < e.results.length; ++i) {
            if (e.results[i].isFinal) {
                value += e.results[i][0].transcript;
                rand = Math.random();
                
            } else {
                value2 += e.results[i][0].transcript;
            }
        }
        document.dispatchEvent(new CustomEvent("GET_TEXT", {detail: {t:value, s:rand}}));
        document.dispatchEvent(new CustomEvent("GET_INTRM", {detail: value2}));

    }
    recognition.onerror = function(e) {
        document.dispatchEvent(new CustomEvent("GET_ONREC", {detail: 'stop'}));
    }
    recognition.start();
    """))

result = streamlit_bokeh_events(
    bokeh_plot = stt_button,
    events="GET_TEXT,GET_ONREC,GET_INTRM",
    key="listen",
    refresh_on_update=False,
    override_height=75,
    debounce_time=0)

tr = st.empty()

if 'input' not in st.session_state:
    st.session_state['input'] = dict(text='', session=0)

tr.text_area("**Your input**", value=st.session_state['input']['text'])

if result:
    if "GET_TEXT" in result:
        if result.get("GET_TEXT")["t"] != '' and result.get("GET_TEXT")["s"] != st.session_state['input']['session'] :
            st.session_state['input']['text'] = result.get("GET_TEXT")["t"]
            tr.text_area("**Your input**", value=st.session_state['input']['text'])
            st.session_state['input']['session'] = result.get("GET_TEXT")["s"]

    if "GET_INTRM" in result:
        if result.get("GET_INTRM") != '':
            tr.text_area("**Your input**", value=st.session_state['input']['text']+' '+result.get("GET_INTRM"))

    if "GET_ONREC" in result:
        if result.get("GET_ONREC") == 'start':
            placeholder.image("recon.gif")
            st.session_state['input']['text'] = ''
        elif result.get("GET_ONREC") == 'running':
            placeholder.image("recon.gif")
        elif result.get("GET_ONREC") == 'stop':
            placeholder.image("recon.jpg")
            if st.session_state['input']['text'] != '':
                input = st.session_state['input']['text']
                output = generate_response(input)
                st.write("**ChatBot:**")
                st.write(output)
                st.session_state['input']['text'] = ''

                tts = gTTS(output, lang='en', tld='com')
                tts.write_to_fp(sound)
                st.audio(sound)

                st.session_state['prompts'].append({"role": "user", "content":input})
                st.session_state['prompts'].append({"role": "assistant", "content":output})





#############################################################################################################
def conversational_chat(query):
    
    result = chain({"question": query, "chat_history": st.session_state['history']})
    st.session_state['history'].append((query, result["answer"]))
    
    return result["answer"]
    
if 'history' not in st.session_state:
    st.session_state['history'] = []

# if 'generated' not in st.session_state:
st.session_state['generated'] = ["Hello ! I am here to help you find your Home! " + " 🤗"]

if 'past' not in st.session_state:
    st.session_state['past'] = ["Hey ! 👋"]
        
    #container for the chat history
response_container = st.container()
#container for the user's text input
container = st.container()

with container:
    with st.form(key='my_form', clear_on_submit=True):
        
        user_input = st.text_input("Query:", placeholder="I am here to help you find your Home! :)", key='input')
        submit_button = st.form_submit_button(label='Send')
        
    if submit_button and user_input:
        output = conversational_chat(user_input)
        
        st.session_state['past'].append(user_input)
        st.session_state['generated'].append(output)

if st.session_state['generated']:
    with response_container:
        for i in range(len(st.session_state['generated'])):
            message(st.session_state["past"][i], is_user=True, key=str(i) + '_user', avatar_style="big-smile")
            message(st.session_state["generated"][i], key=str(i), avatar_style="thumbs")
                
#streamlit run voicebot.py
