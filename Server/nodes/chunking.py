from langchain_text_splitters import RecursiveCharacterTextSplitter


class Chunker:

    def __init__(
        self,
        chunk_size=500,
        chunk_overlap=50
    ):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " ", ""]
        )

    def split_documents(self, documents):

        return self.splitter.split_documents(documents)