import streamlit as st
import requests

# Function to truncate text to a maximum number of words
def truncate_text(text, max_words=30):
    words = text.split()
    if len(words) <= max_words:
        return text
    else:
        truncated_text = ' '.join(words[:max_words]) + '...'
        return truncated_text

# Function to update the database
def update_database(state, question, videos_data, notes_data):
    database_url = st.secrets["DATABASE_URL"]
    
    # Define the payload data
    payload = {
        "state": state,
        "question": question,  # Replace with your question variable
        "videos": videos_data,  # Replace with your llmResponse variable
        "notes": notes_data,  # Replace with your vote variable
    }

    # Define the HTTP headers
    headers = {
        "Content-Type": "application/json",
    }

    # Make the POST request
    response = requests.post(database_url, json=payload, headers=headers)

    # Check the response status code
    if response.status_code == 200:
        # The request was successful
        data = response.json()
        # Handle the response data as needed
    else:
        # Handle the error, e.g., print an error message
        print(f"Error: {response.status_code} - {response.text}")

# Create a SessionState object to manage the app's state
# Session State also supports attribute-based syntax
if 'submitted' not in st.session_state:
    st.session_state.submitted = False

# Streamlit UI elements
st.title("H2 Organic Chemistry Co-pilot")

with st.form(key='question_form'):
    question = st.text_input("Please type in your question here:")
    submit_button = st.form_submit_button("Ask")

if submit_button and question:
    # Update session storage
    st.session_state.submitted = True

if st.session_state.submitted:
    # This magic line makes everything

    # Make a POST request to the Videos API
    videos_api_url = st.secrets["VIDEO_SEARCH_URL"]
    data = {"query_string": question}
    videos_response = requests.post(videos_api_url, json=data)

    # Make a POST request to the Notes API
    notes_api_url = st.secrets["NOTES_SEARCH_URL"]
    notes_response = requests.post(notes_api_url, json=data)

    videos_data = {}
    notes_data = {}

    if videos_response.status_code == 200:
        videos_data = videos_response.json()

    if notes_response.status_code == 200:
        notes_data = notes_response.json()

    # If status code is 200, then the request was successful. Update database
    if videos_response.status_code == 200 and notes_response.status_code == 200:
        update_database("initial", question, videos_data, notes_data)

    # Check if notes or videos data are available
    if len(notes_data) == 0 and len(videos_data) == 0:
        st.write("No relevant documents found.")
    else:
        if len(videos_data) != 0:
            # If there are items in the videos
            st.markdown("Here is what I found from the Lecture Videos:")

            for key, value in videos_data.items():
                st.subheader(f"Video: {value['current_title']} (Score: {value['current_score']})")
                truncated_text = truncate_text(value['current_context'])
                st.write(f"Context: {truncated_text}")
                st.write(f"Link: {value['current_link']}")

        if len(notes_data) != 0:
            # If there are items in the notes
            st.markdown("Here is what I found from the Lecture Notes:")

            # Concatenate the context from notes_data
            concatenated_context = ""
            for key, value in notes_data.items():
                st.subheader(f"Note: Page {value['current_page_number']} (Score: {value['current_score']})")
                truncated_text = truncate_text(value['current_context'])
                st.write(f"Context: {truncated_text}")
                concatenated_context += value['current_context'] + " "

            # Make a POST request to the third API to send the notes output to the LLM
            llm_api_url = st.secrets["LLM_URL"]

            prompt_template = f"""
                To answer the question please only use the Context given, nothing else. Do not make up the answer, simply say 'I don't know' if you are not sure.
                Question: {question}
                Context: {concatenated_context}
                Answer this as accurately and with as much information as possible.
            """

            llm_data = {"query_string": prompt_template}
            llm_response = requests.post(llm_api_url, json=llm_data)

            if llm_response.status_code == 200:
                st.success("Here is what I think...")
                data = llm_response.json()
                response_text = data.get("response", "")
                
                update_database("llm", question, concatenated_context, response_text)

                # Replace line breaks with HTML line breaks
                response_text = response_text.replace("\n", "<br>")

                # Display the response with line breaks
                st.markdown(f"{response_text}", unsafe_allow_html=True)

                # Create a two-column layout for upvote and downvote buttons
                col1, col2 = st.columns(2)

                # Add the upvote button to the first column
                upvote_button = col1.button("Upvote 👍")

                # Add the downvote button to the second column
                downvote_button = col2.button("Downvote 👎")

                if upvote_button:
                    # Make an API call for upvoting
                    update_database("voting", question, concatenated_context, "upvote")
                    st.write("Upvoted!")

                if downvote_button:
                    # Make an API call for downvoting
                    update_database("voting", question, concatenated_context, "downvote")
                    st.write("Downvoted!")

        else:
            st.markdown("I did not find anything from the notes...")

        # Update the session state to indicate that the question has been submitted
        st.session_state.submitted = True
