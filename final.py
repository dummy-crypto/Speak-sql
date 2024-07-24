import streamlit as st
import os
import pandas as pd
import google.generativeai as genai
from dotenv import load_dotenv
import pandasql as ps
import matplotlib.pyplot as plt
import seaborn as sns

# Set the page configuration
st.set_page_config(page_title="SQL Query Retrieval and Visualization App", layout="centered")


# Load custom CSS


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

# Function to automatically generate visualizations
def generate_visualizations(df):
    if df.empty:
        st.warning("The DataFrame is empty. No visualizations can be generated.")
        return
    
    numeric_cols = df.select_dtypes(include='number').columns
    datetime_cols = df.select_dtypes(include='datetime').columns
    categorical_cols = df.select_dtypes(include='object').columns

    st.subheader("Automatic Visualizations")

    fig, axs = plt.subplots(2, 2, figsize=(15, 15))

    # Histogram for the first numeric column
    if len(numeric_cols) > 0:
        sns.histplot(df[numeric_cols[0]], kde=True, ax=axs[0, 0])
        axs[0, 0].set_title(f'Histogram of {numeric_cols[0]}')
    else:
        axs[0, 0].text(0.5, 0.5, 'No numeric columns available for histogram.', 
                       horizontalalignment='center', verticalalignment='center')
    
    # Scatter plot for the first two numeric columns
    if len(numeric_cols) > 1:
        sns.scatterplot(x=df[numeric_cols[0]], y=df[numeric_cols[1]], ax=axs[0, 1])
        axs[0, 1].set_title(f'Scatter Plot of {numeric_cols[0]} vs {numeric_cols[1]}')
    else:
        axs[0, 1].text(0.5, 0.5, 'Not enough numeric columns for scatter plot.', 
                       horizontalalignment='center', verticalalignment='center')
    
    # Line plot for the first datetime column and first numeric column
    if len(datetime_cols) > 0 and len(numeric_cols) > 0:
        df.barplot(datetime_cols[0])[numeric_cols[0]].plot(ax=axs[1, 0])
        axs[1, 0].set_title(f'Line Plot of {numeric_cols[0]} over {datetime_cols[0]}')
    else:
        axs[1, 0].text(0.5, 0.5, 'Not enough datetime or numeric columns for line plot.', 
                       horizontalalignment='center', verticalalignment='center')
    
    # Box plot for the first categorical column and first numeric column
    if len(categorical_cols) > 0 and len(numeric_cols) > 0:
        sns.boxplot(x=df[categorical_cols[0]], y=df[numeric_cols[0]], ax=axs[1, 1])
        axs[1, 1].set_title(f'Box Plot of {numeric_cols[0]} by {categorical_cols[0]}')
    else:
        axs[1, 1].text(0.5, 0.5, 'Not enough categorical or numeric columns for box plot.', 
                       horizontalalignment='center', verticalalignment='center')

    plt.tight_layout()
    st.pyplot(fig)

# Streamlit App
st.title("SpeakSQL")
st.write("Upload a CSV file, record your question, and get the SQL query results!")

if st.button("Load Test Dataset"):
    # You can create a sample DataFrame or load it from a local file
    test_data = {
        'Name': ['Alice', 'Bob', 'Charlie', 'David'],
        'Age': [25, 30, 35, 40],
        'City': ['New York', 'Los Angeles', 'Chicago', 'Houston'],
        'JoinDate': pd.to_datetime(['2021-01-01', '2022-05-15', '2020-07-20', '2019-03-10']),
        'Salary': [50000, 60000, 55000, 70000]
    }
    st.session_state.df = pd.DataFrame(test_data)
    st.session_state.df_name = "df"
    st.success("Test dataset loaded successfully!")
    st.write("Data Preview:")
    st.dataframe(st.session_state.df.head())

# File upload section
uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
if uploaded_file is not None:
    st.session_state.df = pd.read_csv(uploaded_file, parse_dates=True)
    st.session_state.df_name = "df"
    st.success("File uploaded successfully!")
    st.write("Data Preview:")
    st.dataframe(st.session_state.df.head())

# Text area for typing questions
if st.session_state.df is not None:
    # Set the value of the text area to the session state variable
    transcription = st.text_area("Type your Question", value=st.session_state.transcription, height=100)

    df = st.session_state.df
    df_name = st.session_state.df_name

    # Save transcription to session state
    st.session_state.transcription = transcription

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

    if st.button("Get SQL Query", key="record_button"):
        with st.spinner("Generating SQL query..."):
            response = get_gemini_response(transcription, prompt)
            st.success("SQL query generated!")

        sql_query = response.strip().split(';')[0].strip()
        st.code(sql_query, language='sql')

        with st.spinner("Executing SQL query..."):
            try:
                result_df = read_sql_query(sql_query, df)
                st.success("Query executed!")
                st.subheader("Query Results")
                st.dataframe(result_df)

                # Generate automatic visualizations
                if not result_df.empty:
                    generate_visualizations(result_df)
                else:
                    st.warning("No data available to visualize.")
            except Exception as e:
                st.error(f"Query error: {e}")
