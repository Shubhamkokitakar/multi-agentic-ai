from langchain_community.document_loaders import WebBaseLoader

urls = [

    "https://archive.cdc.gov/#/details?url=https://www.cdc.gov/covid/vaccines/faq.html",

    "https://www.who.int/news-room/questions-and-answers/item/coronavirus-disease-(covid-19)-vaccines"
]

loader = WebBaseLoader(urls)

docs = loader.load()

print(f"\nTotal Documents Loaded: {len(docs)}")

print("\nFIRST DOCUMENT:\n")

print(docs[0].page_content[:3000])