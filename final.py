import streamlit as st
import os
import pandas as pd
import google.generativeai as genai
from dotenv import load_dotenv
import pandasql as ps

# Set the page configuration
st.set_page_config(page_title="SQL Query Retrieval App", layout="centered")

# Custom CSS for a fancy background and styling
st.markdown(
    """
    <style>
    body {
        background-image: url('https://www.example.com/background.jpg');
        background-size: cover;
        background-attachment: fixed;
        font-family: Arial, sans-serif;  /* Change the font for better readability */
    }
    .stApp {
        background: rgba(255, 255, 255, 0.95);  /* Adjusted opacity for readability */
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    }
    h1 {
        color: #333333;
        text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.2);
        font-size: 2.5rem;  /* Larger font size for title */
        text-align: center;  /* Center align the title */
        margin-bottom: 1.5rem;  /* Add margin for spacing */
    }
    h2 {
        color: #4CAF50;  /* Green color for section headers */
        font-size: 1.8rem;  /* Slightly larger font for section headers */
        margin-top: 2rem;  /* Add top margin for separation */
        margin-bottom: 1rem;  /* Add bottom margin for spacing */
    }
    .btn-primary {
        background-color: #4CAF50;  /* Green background for primary button */
        color: white;  /* White text for contrast */
        padding: 0.8rem 1.2rem;  /* Padding adjustment for button size */
        font-size: 1rem;  /* Adjust font size */
        border-radius: 8px;  /* Rounded corners */
        transition: background-color 0.3s ease;  /* Smooth transition */
    }
    .btn-primary:hover {
        background-color: #45A049;  /* Darker shade on hover */
    }
    .stTextInput {
        background-color: #f2f2f2;  /* Light gray background for text input */
        padding: 0.6rem;  /* Adjust padding for input field */
        border-radius: 8px;  /* Rounded corners */
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Load environment variables
load_dotenv()

# Initialize session state variables
if 'transcription' not in st.session_state:
    st.session_state.transcription = ""

if 'df' not in st.session_state:
    st.session_state.df = None

if 'df_name' not in st.session_state:
    st.session_state.df_name = ""


# Configure GenAI key
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Function to load Google Gemini Model and provide queries as response
def get_gemini_response(question, prompt):
    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content([prompt[0], question])
    return response.text

# Function to retrieve query from the DataFrame using eval
def read_sql_query(sql, df):
    try:
        result_df = ps.sqldf(sql, locals())
        return result_df
    except Exception as e:
        st.error(f"Query error: {e}")
        return pd.DataFrame()

# Streamlit App
st.title("SpeakSQL")
st.write("Upload a CSV file, record your question, and get the SQL query results!")

# File upload section
uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
if uploaded_file is not None:
    st.session_state.df = pd.read_csv(uploaded_file)
    st.session_state.df_name = "df"
    st.success("File uploaded successfully!")
    st.write("Data Preview:")
    st.dataframe(st.session_state.df.head())

    # Question input section
    transcription = st.text_area("Type your Question", value=st.session_state.transcription, height=100, class="stTextInput")

    df = st.session_state.df
    df_name = st.session_state.df_name

    # Dynamically create the prompt based on the DataFrame columns
    columns = ', '.join(df.columns)
    prompt = [
        f"""
        You are an expert in converting English questions to SQL query!
        The SQL database has the name {df_name} and has the following columns - {columns}.
        
        For example:
        Example 1 - How many entries of records are present?, the SQL command will be something like this:
        SELECT COUNT(*) FROM {df_name};
        
        Example 2 - Tell me all the entries where {df.columns[0]} is equal to "value", the SQL command will be something like this:
        SELECT * FROM {df_name} WHERE {df.columns[0]}="value";
        
        Please do not include ``` at the beginning or end and the SQL keyword in the output.
        """
    ]

    if st.button("Get SQL Query", class="btn-primary"):
        with st.spinner("Generating SQL query..."):
            response = get_gemini_response(transcription, prompt)
            st.success("SQL query generated!")
        
        sql_query = response.strip().split(';')[0].strip()
        
        st.code(sql_query, language='sql')
        
        with st.spinner("Executing SQL query..."):
            try:
                result = read_sql_query(sql_query, df)
                st.success("Query executed!")
                st.subheader("Query Results")
                st.dataframe(result)
            except Exception as e:
                st.error(f"Query error: {e}")
