"""
RestorAI Knowledge Base Ingestion Script
Lab 2: Knowledge Engineering & Domain Grounding

This script processes furniture restoration guides, performs semantic chunking,
adds metadata tags, generates embeddings, and stores them in ChromaDB.

Author: Abdullah Noor - 2022029
Domain: Furniture Restoration & Image Analysis
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime
import chromadb
from chromadb.config import Settings
from openai import OpenAI

# Try to load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not required if env vars are set manually


class RestorationDataIngestion:
    """
    Handles data ingestion for RestorAI furniture restoration knowledge base.
    
    Performs:
    1. File reading and cleaning
    2. Semantic chunking based on content structure
    3. Metadata enrichment (3+ tags per chunk)
    4. Embedding generation
    5. Vector database storage
    """
    
    def __init__(self, data_directory: str, collection_name: str = "restoration_knowledge"):
        """
        Initialize the ingestion pipeline.
        
        Args:
            data_directory: Path to directory containing restoration guide files
            collection_name: Name of ChromaDB collection
        """
        self.data_directory = Path(data_directory)
        self.collection_name = collection_name
        
        # Initialize ChromaDB client (persistent storage)
        self.chroma_client = chromadb.PersistentClient(
            path="./chroma_db",
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Initialize OpenAI client for embeddings
        api_key = "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"
        os.environ["CHROMA_TELEMETRY_IMPL"] = "None"
        if not api_key:
            print("\n" + "="*70)
            print("❌ ERROR: OpenAI API key not found!")
            print("="*70)
            print("\nPlease set your OpenAI API key using one of these methods:\n")
            print("Method 1: Environment Variable (PowerShell)")
            print("  $env:OPENAI_API_KEY=\"your_api_key_here\"")
            print("\nMethod 2: Create a .env file in the project root:")
            print("  OPENAI_API_KEY=your_api_key_here")
            print("\nMethod 3: Command Prompt")
            print("  set OPENAI_API_KEY=your_api_key_here")
            print("\nGet your API key from: https://platform.openai.com/api-keys")
            print("="*70)
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        
        self.openai_client = OpenAI(api_key=api_key)
        
        # Create or get collection
        self.collection = self.chroma_client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "Furniture restoration knowledge base for RestorAI"}
        )
        
        print(f"✓ Initialized ChromaDB collection: '{self.collection_name}'")
        print(f"✓ Data directory: {self.data_directory.absolute()}")
    
    def clean_text(self, raw_text: str) -> str:
        """
        Clean raw text by removing excessive whitespace, normalizing formatting.
        
        Domain-specific cleaning:
        - Remove multiple consecutive blank lines
        - Normalize whitespace
        - Remove trailing/leading spaces
        - Preserve section markers (===)
        
        Args:
            raw_text: Raw text from file
            
        Returns:
            Cleaned text
        """
        # Remove Windows carriage returns
        text = raw_text.replace('\r\n', '\n')
        
        # Remove excessive blank lines (more than 2 consecutive)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove trailing whitespace from each line
        text = '\n'.join(line.rstrip() for line in text.split('\n'))
        
        # Normalize spaces (multiple spaces to single)
        text = re.sub(r' {2,}', ' ', text)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def extract_metadata_from_header(self, text: str) -> Dict[str, str]:
        """
        Extract metadata from document header.
        
        Looks for structured metadata in format:
        Source: ...
        Last Updated: ...
        Category: ...
        Priority: ...
        
        Args:
            text: Document text
            
        Returns:
            Dictionary of metadata fields
        """
        metadata = {}
        
        # Extract structured header fields
        patterns = {
            'source': r'Source:\s*(.+)',
            'last_updated': r'Last Updated:\s*(.+)',
            'category': r'Category:\s*(.+)',
            'priority': r'Priority:\s*(.+)',
            'doc_type': r'GUIDE\s*-\s*(.+)',
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                metadata[key] = match.group(1).strip()
        
        return metadata
    
    def semantic_chunking(self, text: str, filename: str) -> List[Tuple[str, Dict[str, str]]]:
        """
        Perform semantic chunking based on content structure.
        
        Strategy:
        - Split by major sections (=== markers)
        - Keep related information together (e.g., full technique description)
        - Maintain context by including section titles
        - Add rich metadata to each chunk
        
        Args:
            text: Cleaned document text
            filename: Source filename for metadata
            
        Returns:
            List of (chunk_text, metadata) tuples
        """
        chunks = []
        
        # Extract document-level metadata from header
        doc_metadata = self.extract_metadata_from_header(text)
        
        # Split by major sections (=== Section Name ===)
        section_pattern = r'(===\s*(.+?)\s*===)'
        sections = re.split(section_pattern, text)
        
        # Process sections
        current_section_title = "Introduction"
        current_content = []
        
        for i, part in enumerate(sections):
            if part.startswith('==='):
                # This is a section marker
                if current_content:
                    # Save previous section
                    chunk_text = '\n'.join(current_content).strip()
                    if chunk_text and len(chunk_text) > 100:  # Minimum chunk size
                        metadata = self._create_chunk_metadata(
                            chunk_text, 
                            current_section_title,
                            filename,
                            doc_metadata
                        )
                        chunks.append((chunk_text, metadata))
                
                # Start new section
                current_section_title = sections[i+1].strip() if i+1 < len(sections) else "Unknown"
                current_content = [part]  # Include section header
            else:
                # This is content
                if part.strip():
                    current_content.append(part.strip())
        
        # Add final section
        if current_content:
            chunk_text = '\n'.join(current_content).strip()
            if chunk_text and len(chunk_text) > 100:
                metadata = self._create_chunk_metadata(
                    chunk_text,
                    current_section_title,
                    filename,
                    doc_metadata
                )
                chunks.append((chunk_text, metadata))
        
        return chunks
    
    def _create_chunk_metadata(
        self, 
        chunk_text: str, 
        section_title: str,
        filename: str,
        doc_metadata: Dict[str, str]
    ) -> Dict[str, str]:
        """
        Create rich metadata for a text chunk.
        
        Required: At least 3 metadata tags per chunk
        
        Metadata includes:
        1. section_name: Section this chunk belongs to
        2. doc_type: Type of document (repair, material, safety, etc.)
        3. material_type: Materials mentioned (wood, veneer, hardware)
        4. damage_type: Types of damage discussed
        5. difficulty_level: Skill level required
        6. safety_level: Safety considerations
        7. source_file: Original filename
        8. priority: Priority level for retrieval
        9. content_category: High-level categorization
        10. timestamp: Ingestion timestamp
        
        Args:
            chunk_text: Text content of chunk
            section_title: Section title
            filename: Source filename
            doc_metadata: Document-level metadata
            
        Returns:
            Dictionary of metadata tags
        """
        metadata = {
            'section_name': section_title,
            'source_file': filename,
            'timestamp': datetime.now().isoformat(),
        }
        
        # Add document-level metadata
        metadata.update(doc_metadata)
        
        # Infer metadata from content
        chunk_lower = chunk_text.lower()
        
        # Material type detection
        materials = []
        if any(word in chunk_lower for word in ['oak', 'walnut', 'mahogany', 'pine', 'maple', 'cherry', 'wood']):
            materials.append('wood')
        if 'veneer' in chunk_lower:
            materials.append('veneer')
        if any(word in chunk_lower for word in ['brass', 'bronze', 'iron', 'steel', 'hardware']):
            materials.append('hardware')
        if 'shellac' in chunk_lower or 'lacquer' in chunk_lower or 'finish' in chunk_lower:
            materials.append('finish')
        
        metadata['material_type'] = ','.join(materials) if materials else 'general'
        
        # Damage type detection
        damage_types = []
        if 'water ring' in chunk_lower or 'water mark' in chunk_lower:
            damage_types.append('water_damage')
        if 'scratch' in chunk_lower or 'gouge' in chunk_lower:
            damage_types.append('scratches')
        if 'veneer' in chunk_lower and ('bubble' in chunk_lower or 'lift' in chunk_lower):
            damage_types.append('veneer_damage')
        if 'oxidation' in chunk_lower or 'darkening' in chunk_lower:
            damage_types.append('oxidation')
        if 'crack' in chunk_lower or 'split' in chunk_lower:
            damage_types.append('cracking')
        
        metadata['damage_type'] = ','.join(damage_types) if damage_types else 'none'
        
        # Difficulty level detection
        if any(word in chunk_lower for word in ['easy', 'simple', 'basic']):
            metadata['difficulty_level'] = 'easy'
        elif any(word in chunk_lower for word in ['medium', 'moderate', 'intermediate']):
            metadata['difficulty_level'] = 'medium'
        elif any(word in chunk_lower for word in ['hard', 'difficult', 'advanced', 'professional']):
            metadata['difficulty_level'] = 'hard'
        else:
            metadata['difficulty_level'] = 'unspecified'
        
        # Safety level detection
        if any(word in chunk_lower for word in ['danger', 'hazard', 'warning', 'toxic', 'flammable', 'safety']):
            metadata['safety_level'] = 'high_caution'
        elif any(word in chunk_lower for word in ['caution', 'wear gloves', 'ventilation']):
            metadata['safety_level'] = 'moderate_caution'
        else:
            metadata['safety_level'] = 'standard'
        
        # Content category (high-level)
        if 'safety' in filename.lower() or metadata.get('category', '').lower() == 'safety':
            metadata['content_category'] = 'safety'
        elif 'material' in filename.lower() or 'identification' in chunk_lower:
            metadata['content_category'] = 'identification'
        elif 'finish' in filename.lower() or 'finishing' in section_title.lower():
            metadata['content_category'] = 'finishing'
        elif 'product' in filename.lower():
            metadata['content_category'] = 'products'
        else:
            metadata['content_category'] = 'techniques'
        
        # Process type (for agent routing)
        if any(word in chunk_lower for word in ['strip', 'sand', 'remove']):
            metadata['process_type'] = 'removal'
        elif any(word in chunk_lower for word in ['apply', 'coat', 'finish', 'stain']):
            metadata['process_type'] = 'application'
        elif any(word in chunk_lower for word in ['repair', 'fix', 'glue']):
            metadata['process_type'] = 'repair'
        elif any(word in chunk_lower for word in ['identify', 'test', 'determine']):
            metadata['process_type'] = 'diagnosis'
        else:
            metadata['process_type'] = 'general'
        
        return metadata
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text using OpenAI's embedding model.
        
        Uses: text-embedding-3-small (1536 dimensions)
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        response = self.openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
    
    def process_file(self, filepath: Path) -> int:
        """
        Process a single restoration guide file.
        
        Args:
            filepath: Path to file
            
        Returns:
            Number of chunks created
        """
        print(f"\n📄 Processing: {filepath.name}")
        
        # Read file
        with open(filepath, 'r', encoding='utf-8') as f:
            raw_text = f.read()
        
        # Clean text
        cleaned_text = self.clean_text(raw_text)
        print(f"  ✓ Cleaned text ({len(cleaned_text)} chars)")
        
        # Semantic chunking
        chunks = self.semantic_chunking(cleaned_text, filepath.name)
        print(f"  ✓ Created {len(chunks)} semantic chunks")
        
        # Generate embeddings and store
        chunk_count = 0
        for i, (chunk_text, metadata) in enumerate(chunks):
            # Generate embedding
            embedding = self.generate_embedding(chunk_text)
            
            # Create unique ID
            chunk_id = f"{filepath.stem}_chunk_{i}_{datetime.now().timestamp()}"
            
            # Store in ChromaDB
            self.collection.add(
                ids=[chunk_id],
                embeddings=[embedding],
                documents=[chunk_text],
                metadatas=[metadata]
            )
            
            chunk_count += 1
            
            # Print sample metadata for first chunk
            if i == 0:
                print(f"  ✓ Sample metadata: {metadata}")
        
        print(f"  ✓ Stored {chunk_count} chunks with embeddings")
        return chunk_count
    
    def ingest_all(self) -> Dict[str, int]:
        """
        Process all files in the data directory.
        
        Returns:
            Dictionary with statistics
        """
        print("\n" + "="*70)
        print("RestorAI Knowledge Base Ingestion")
        print("="*70)
        
        # Find all .txt files in data directory
        txt_files = list(self.data_directory.rglob("*.txt"))
        
        if not txt_files:
            print(f"⚠ No .txt files found in {self.data_directory}")
            return {'files_processed': 0, 'total_chunks': 0}
        
        print(f"\n📚 Found {len(txt_files)} restoration guide files")
        
        total_chunks = 0
        for filepath in txt_files:
            chunks = self.process_file(filepath)
            total_chunks += chunks
        
        # Get collection stats
        collection_count = self.collection.count()
        
        print("\n" + "="*70)
        print("✅ INGESTION COMPLETE")
        print("="*70)
        print(f"Files processed: {len(txt_files)}")
        print(f"Total chunks created: {total_chunks}")
        print(f"ChromaDB collection count: {collection_count}")
        print(f"Collection name: '{self.collection_name}'")
        print(f"Storage location: ./chroma_db")
        print("="*70)
        
        return {
            'files_processed': len(txt_files),
            'total_chunks': total_chunks,
            'collection_count': collection_count
        }
    
    def query_test(self, query: str, n_results: int = 3, metadata_filter: Dict = None) -> List[Dict]:
        """
        Test query against the knowledge base.
        
        Args:
            query: Search query
            n_results: Number of results to return
            metadata_filter: Optional metadata filter
            
        Returns:
            List of results with documents and metadata
        """
        # Generate query embedding
        query_embedding = self.generate_embedding(query)
        
        # Query collection
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=metadata_filter
        )
        
        # Format results
        formatted_results = []
        for i in range(len(results['ids'][0])):
            formatted_results.append({
                'id': results['ids'][0][i],
                'document': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'distance': results['distances'][0][i] if 'distances' in results else None
            })
        
        return formatted_results


def main():
    """
    Main ingestion pipeline execution.
    """
    # Configuration
    DATA_DIR = "./data/restoration_guides"
    COLLECTION_NAME = "restoration_knowledge"
    
    # Check if data directory exists
    if not os.path.exists(DATA_DIR):
        print(f"❌ Error: Data directory not found: {DATA_DIR}")
        print("Please ensure restoration guide files are in the correct location.")
        return
    
    # Initialize ingestion pipeline
    ingestion = RestorationDataIngestion(
        data_directory=DATA_DIR,
        collection_name=COLLECTION_NAME
    )
    
    # Process all files
    stats = ingestion.ingest_all()
    
    # Run sample test query
    if stats['total_chunks'] > 0:
        print("\n" + "="*70)
        print("🔍 SAMPLE TEST QUERY")
        print("="*70)
        query = "How do I remove water rings from wood furniture?"
        print(f"Query: '{query}'")
        print()
        
        results = ingestion.query_test(query, n_results=2)
        
        for i, result in enumerate(results, 1):
            print(f"\nResult {i}:")
            print(f"  Metadata: {result['metadata']}")
            print(f"  Excerpt: {result['document'][:200]}...")
            print(f"  Relevance: {1 - result['distance']:.3f}")


if __name__ == "__main__":
    main()
