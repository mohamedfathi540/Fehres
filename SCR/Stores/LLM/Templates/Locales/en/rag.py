from string import Template


### RAG prompt ###

### System Prompt ###

system_prompt = Template("\n".join([
    "you are assistant genrate a respone for the user .",
    "you will be provided by a set of document associated with the user's query .",
    "you hve to generate a response based on the provided documents .",
    "Ignore any documents that are not relevant to the user's query .",
    "you can apoligize if you do not have enough information to answer the user's query .",
    "you have to genrate respone in th same language as the user's query .",
    "Be polite respectful and professional with the user .",
    "be precise and accurate and concise in your response , Avoid any unnecessary information .",
]))


### Document Prompt ###

document_prompt = Template(
    "\n".join([
    "## Document NO:$doc_num",
    "### Content :$chunk_text",
]))



### Footer Prompt ###

footer_prompt = Template(
    "\n".join([
    "Based only on the above documents , please generate an answer to the user's query .",
    "## Question : ",
    "$query" ,
    " ",
    "## Answer :",
]))