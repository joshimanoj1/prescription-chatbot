# rag_search.py
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.documents import Document

def setup_rag_pipeline(prescription_text, hindi_text, openai_api_key):
    # Initialize embeddings and LLM
    embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
    llm = ChatOpenAI(model_name="gpt-4o", openai_api_key=openai_api_key)

    # Combine English and Hindi prescription text into a single document
    combined_text = f"English Prescription:\n{prescription_text}\n\nHindi Prescription:\n{hindi_text}"
    
    # Create a Document object with metadata
    documents = [Document(page_content=combined_text, metadata={"source": "prescription"})]

    # Create a vector store with the documents
    vector_store = FAISS.from_documents(documents, embeddings)

    # Set up the retriever
    retriever = vector_store.as_retriever(search_kwargs={"k": 2})

    # Define the prompt template
    prompt_template = """Use the following pieces of context to answer the user's question.
    The context includes the prescription text, which should be the primary source of information.
    If the prescription text does not contain the requested information, explicitly state that. Provide an answer based on general knowledge. 
    ONLY If the context includes additional web information and the user has requested more information, provide a more DETAILED response, including specific use cases, side effects, contraindications, or alternative approaches.Do NOT use your own knowledge to generate the response. 
    ----------------
    {context}

    Question: {question}
    """
    prompt = PromptTemplate(template=prompt_template, input_variables=["context", "question"])

    # Set up the RAG chain
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True,
        chain_type_kwargs={"prompt": prompt}
    )

    return qa_chain

def answer_question(qa_chain, question, conversation_history, prescription_text=None, web_info=None):
    # Step 1: Use the RAG pipeline to search the prescription text
    full_query = f"Conversation History:\n{conversation_history}\n\nCurrent Question: {question}"
    result = qa_chain({"query": full_query})
    answer = result["result"]
    source_documents = result["source_documents"]

    # Step 2: Check if the answer is sufficient
    insufficient_answer = (
        "I don't have enough information" in answer.lower() or
        "not mentioned" in answer.lower() or
        len(answer) < 50 or
        "alternatives" in question.lower() and "alternatives" not in answer.lower()
    )

    # Step 3: If the answer is insufficient and no web info is provided, return the answer with a note
    if insufficient_answer and not web_info:
        answer = (
            f"The prescription text does not contain specific information about {question}. "
            f"Here is a general answer based on available knowledge:\n\n{answer}"
        )
        return answer, source_documents

    # Step 4: If web info is provided (e.g., after "I need more information"), include it in the answer
    if web_info:
        # Combine web info text for the context
        web_info_text = "\n\n".join([f"Web Info from {item['url']}:\n{item['text']}" for item in web_info])
        full_query_with_web = (
            f"Conversation History:\n{conversation_history}\n\n"
            f"Current Question: {question}\n\n"
            f"Prescription Information:\n{prescription_text}\n\n"
            f"Additional Info from Web: {web_info_text}"
        )
        result = qa_chain({"query": full_query_with_web})
        answer = result["result"]
        source_documents = result["source_documents"]
        # Append web info to source_documents
        for item in web_info:
            source_documents.append(Document(page_content=item["text"], metadata={"source": item["url"]}))

    return answer, source_documents