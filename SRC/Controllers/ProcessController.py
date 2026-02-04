from .BaseController import basecontroller
from .ProjectController import projectcontroller
from Helpers.Config import get_settings
import os
import json
from langchain_community.document_loaders import TextLoader
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_community.document_loaders import CSVLoader
from langchain_community.document_loaders import Docx2txtLoader
from Models import processingEnum
from typing import List
from dataclasses import dataclass

# Domain keywords for learning books (maths, statistics, coding, ml, dl, genai, system_design)
DOMAIN_KEYWORDS = ("maths", "statistics", "probability", "coding", "system_design", "system design", "ml", "dl", "genai", "gen ai")

@dataclass
class Document :
    page_content : str
    metadata : dict

class processcontroller (basecontroller) :

    def __init__(self, project_id : str):
        super().__init__()

        self.project_id = project_id
        self.project_path = projectcontroller().get_project_path(project_id = project_id)

    def get_file_extension(self , file_id : str) :
        return os.path.splitext(file_id)[-1].lower()
        

    def get_file_loader(self,file_id : str ) :
        file_ext = self.get_file_extension(file_id = file_id)
        file_path = os.path.join (
            self.project_path,
            file_id
        )
        
        print(f"[DEBUG] get_file_loader: Checking path: {file_path}")
        if not os.path.exists(file_path):
            print(f"[ERROR] get_file_loader: File not found at {file_path}")
            return None
        
        if file_ext == processingEnum.TXT.value :
           return TextLoader( file_path,encoding= "utf-8")
        
        if file_ext == processingEnum.PDF.value :
            return PyMuPDFLoader(file_path)

        if file_ext == processingEnum.MD.value :
           return TextLoader( file_path,encoding= "utf-8")

        if file_ext == processingEnum.JSON.value :
           return TextLoader( file_path,encoding= "utf-8")

        if file_ext == processingEnum.CSV.value :
           return CSVLoader( file_path,encoding= "utf-8")

        if file_ext == processingEnum.DOCX.value :
           return Docx2txtLoader( file_path)

        print(f"[ERROR] get_file_loader: Unsupported file extension {file_ext}")
        return None
    
    def get_file_content (self, file_id : str) :
        file_path = os.path.join(self.project_path, file_id)
        if not os.path.exists(file_path):
            print(f"[ERROR] get_file_content: File not found at {file_path}")
            return None
        if not os.access(file_path, os.R_OK):
            print(f"[ERROR] get_file_content: File not readable (permissions) at {file_path}")
            return None

        loader = self.get_file_loader(file_id=file_id)
        if not loader:
            return None
        try:
            return loader.load()
        except Exception as e:
            err_msg = str(e)
            print(f"[ERROR] get_file_content: Failed to load content for {file_id}. Error: {err_msg}")
            if "encrypted" in err_msg.lower() or "password" in err_msg.lower():
                print("[HINT] PDF may be password-protected; try removing protection or use an unprotected copy.")
            elif "failed to open" in err_msg.lower() or "cannot open" in err_msg.lower():
                print("[HINT] PDF may be corrupted, encrypted, or in an unsupported format; try re-exporting or a different PDF.")
            raise

    def get_domain_for_file(self, file_id: str) -> str:
        """Infer domain for chunk metadata from config BOOK_DOMAIN_MAPPING or filename keywords."""
        try:
            settings = get_settings()
            if getattr(settings, "BOOK_DOMAIN_MAPPING", None):
                mapping = json.loads(settings.BOOK_DOMAIN_MAPPING)
                if isinstance(mapping, dict) and file_id in mapping:
                    return str(mapping[file_id])
        except (json.JSONDecodeError, TypeError):
            pass
        base = os.path.splitext(file_id)[0].lower()
        for kw in DOMAIN_KEYWORDS:
            if kw.replace(" ", "_") in base.replace("-", "_").replace(" ", "_") or kw in base:
                return kw.replace(" ", "_")
        return ""

    def process_file_content(self, file_content :list , file_id :str ,chunk_size : int = 100 , overlap_size :int = 20) :
        

        file_content_texts = [
            rec.page_content
            for rec in file_content 
            
        ]

        file_content_metadata = [rec.metadata or {} for rec in file_content]
        enriched_metadatas = [
            {**m, "source": file_id, "file_name": file_id, "domain": self.get_domain_for_file(file_id)}
            for m in file_content_metadata
        ]

        chunks = self.process_simpler_splitter(
            texts=file_content_texts,
            metadatas=enriched_metadatas,
            chunk_size=chunk_size,
            overlap_size=overlap_size,
            splitter_tag="\n",
        )

        return chunks

    def _split_segment_into_chunks(self, text: str, chunk_size: int, overlap_size: int, splitter_tag: str) -> List[str]:
        """Split a single segment (e.g. one page) into chunk strings with overlap (sliding window)."""
        overlap_size = max(0, min(overlap_size, chunk_size - 1))
        lines = [doc.strip() for doc in text.split(splitter_tag) if len(doc.strip()) > 1]
        chunk_strings = []
        current_chunk = ""
        for line in lines:
            current_chunk += line + splitter_tag
            if len(current_chunk) >= chunk_size:
                chunk_strings.append(current_chunk.strip())
                if overlap_size > 0 and len(current_chunk) > overlap_size:
                    current_chunk = current_chunk[-overlap_size:]
                else:
                    current_chunk = ""
        if len(current_chunk) > 0:
            chunk_strings.append(current_chunk.strip())
        return chunk_strings

    def process_simpler_splitter(
        self,
        texts: List[str],
        metadatas: List[dict],
        chunk_size: int,
        overlap_size: int = 20,
        splitter_tag: str = "\n",
    ) -> List[Document]:
        """Split texts per segment, assigning segment metadata and chunk_order to each chunk."""
        if not texts or not metadatas:
            return []
        overlap_size = max(0, overlap_size or 0)
        if len(metadatas) < len(texts):
            metadatas = metadatas + [metadatas[-1] if metadatas else {}] * (len(texts) - len(metadatas))
        elif len(metadatas) > len(texts):
            metadatas = metadatas[: len(texts)]
        chunks = []
        for text, meta in zip(texts, metadatas):
            segment_chunks = self._split_segment_into_chunks(text, chunk_size, overlap_size, splitter_tag)
            for i, chunk_text in enumerate(segment_chunks):
                chunks.append(
                    Document(
                        page_content=chunk_text,
                        metadata={**meta, "chunk_order": i + 1},
                    )
                )
        return chunks
