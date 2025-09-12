"""
IDF (Inverse Document Frequency) Calculator for Enhanced Semantic Analysis.

This module calculates term importance weights from document corpus analysis,
enabling the semantic analyzer to better identify high-value instructional content
by understanding which chess terms are rare vs common across the collection.
"""

import logging
import json
import hashlib
import math
from datetime import datetime
from collections import Counter
from typing import Dict, Any, List, Optional
from pathlib import Path

from ..core.models import IDFWeights
from ..core.constants import ChessVocabulary

try:
    from tqdm import tqdm

    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False


    # Fallback progress indicator
    class tqdm:
        def __init__(self, iterable=None, total=None, desc=None, **kwargs):
            self.iterable = iterable
            self.total = total or (len(iterable) if iterable else 0)
            self.desc = desc
            self.n = 0
            if desc:
                print(f"Starting: {desc}")

        def __iter__(self):
            for item in self.iterable:
                yield item
                self.update(1)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            if self.desc:
                print(f"Completed: {self.desc}")

        def update(self, n=1):
            self.n += n
            if self.total and self.n % max(1, self.total // 20) == 0:
                percent = (self.n / self.total) * 100
                print(f"Progress: {self.n}/{self.total} ({percent:.1f}%)")

        def set_description(self, desc):
            self.desc = desc

        def set_postfix(self, postfix_dict):
            pass

        def close(self):
            pass


class IDFCalculator:
    """
    Calculate IDF weights from document corpus for enhanced semantic analysis.

    The IDF system helps identify which chess terms are rare and valuable vs
    common across the corpus. This enables better instructional content detection
    by giving higher weights to sophisticated chess terminology that appears
    in educational content.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def calculate_corpus_idf(self, documents: List[str],
                             chess_concepts: Optional[Dict[str, List[str]]] = None) -> IDFWeights:
        """
        Calculate IDF weights with progress tracking and interruption handling.

        Args:
            documents: List of document texts to analyze
            chess_concepts: Chess vocabulary dict (uses default if None)

        Returns:
            IDFWeights object containing calculated term weights
        """
        if chess_concepts is None:
            chess_concepts = ChessVocabulary.get_chess_concepts()

        self.logger.info(f"Calculating IDF weights for {len(documents)} documents")

        # Flatten all chess terms
        all_terms = []
        for category, terms in chess_concepts.items():
            all_terms.extend([term.lower() for term in terms])

        # Remove duplicates while preserving order
        unique_terms = list(dict.fromkeys(all_terms))

        self.logger.info(f"Analyzing {len(unique_terms)} unique chess terms across corpus")

        # Count document frequencies with progress bar
        term_doc_counts = Counter()
        total_docs = len(documents)

        with tqdm(total=total_docs, desc="🔍 Analyzing documents for IDF calculation",
                  unit="docs", miniters=max(1, total_docs // 100)) as pbar:

            for doc_idx, document in enumerate(documents):
                try:
                    doc_lower = document.lower()
                    doc_terms = set()

                    # Find terms present in this document
                    for term in unique_terms:
                        if term in doc_lower:
                            doc_terms.add(term)

                    # Count each unique term once per document
                    for term in doc_terms:
                        term_doc_counts[term] += 1

                    # Update progress
                    pbar.update(1)

                    # Update description with current stats every 100 docs
                    if doc_idx % 100 == 0 and doc_idx > 0:
                        unique_terms_found = len([t for t in term_doc_counts.values() if t > 0])
                        pbar.set_description(f"🔍 Doc {doc_idx}/{total_docs} | {unique_terms_found} terms found")

                except Exception as e:
                    self.logger.warning(f"Error processing document {doc_idx}: {e}")
                    continue

        # Calculate IDF weights with progress
        self.logger.info("Computing IDF weights from document frequencies...")
        term_weights = {}

        with tqdm(total=len(unique_terms), desc="📊 Computing IDF weights", unit="terms") as pbar:
            for term in unique_terms:
                doc_freq = term_doc_counts[term]
                if doc_freq > 0:
                    # Standard IDF formula with smoothing
                    idf = math.log((total_docs + 1) / (doc_freq + 1))
                    term_weights[term] = idf
                else:
                    # Term not found in any document - assign high weight
                    term_weights[term] = math.log(total_docs + 1)

                pbar.update(1)

        # Create corpus hash for validation
        self.logger.info("Creating corpus validation hash...")
        corpus_sample = " ".join(documents[:100])  # Sample for hashing
        corpus_hash = hashlib.md5(corpus_sample.encode()).hexdigest()

        weights = IDFWeights(
            term_weights=term_weights,
            total_documents=total_docs,
            vocabulary_size=len(term_weights),
            calculation_date=datetime.now().isoformat(),
            corpus_hash=corpus_hash
        )

        avg_idf = sum(term_weights.values()) / len(term_weights)
        self.logger.info(f"IDF calculation complete: {len(term_weights)} terms, avg IDF: {avg_idf:.3f}")

        # Log some statistics for verification
        self._log_idf_statistics(term_weights, term_doc_counts, total_docs)

        return weights

    def _log_idf_statistics(self, term_weights: Dict[str, float],
                            term_doc_counts: Counter, total_docs: int):
        """Log IDF calculation statistics for verification"""
        # Find highest and lowest IDF terms
        sorted_terms = sorted(term_weights.items(), key=lambda x: x[1], reverse=True)

        self.logger.info("IDF Statistics:")
        self.logger.info(f"  Total documents: {total_docs}")
        self.logger.info(f"  Terms analyzed: {len(term_weights)}")

        # Top 10 rare terms (highest IDF)
        self.logger.info("  Top 10 rare terms (high IDF):")
        for term, idf in sorted_terms[:10]:
            doc_count = term_doc_counts[term]
            self.logger.info(f"    {term}: IDF={idf:.3f} (in {doc_count}/{total_docs} docs)")

        # Bottom 10 common terms (lowest IDF)
        self.logger.info("  Top 10 common terms (low IDF):")
        for term, idf in sorted_terms[-10:]:
            doc_count = term_doc_counts[term]
            self.logger.info(f"    {term}: IDF={idf:.3f} (in {doc_count}/{total_docs} docs)")

    def save_idf_weights(self, weights: IDFWeights, filepath: str):
        """
        Save IDF weights to file.

        Args:
            weights: IDFWeights object to save
            filepath: Path to save the weights file
        """
        try:
            # Ensure directory exists
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)

            # Save weights with pretty formatting
            with open(filepath, 'w') as f:
                weights_dict = {
                    'metadata': {
                        'total_documents': weights.total_documents,
                        'vocabulary_size': weights.vocabulary_size,
                        'calculation_date': weights.calculation_date,
                        'corpus_hash': weights.corpus_hash
                    },
                    'term_weights': weights.term_weights
                }
                json.dump(weights_dict, f, indent=2, sort_keys=True)

            self.logger.info(f"IDF weights saved to {filepath}")

            # Save summary statistics
            summary_path = filepath.replace('.json', '_summary.txt')
            self._save_summary_statistics(weights, summary_path)

        except Exception as e:
            self.logger.error(f"Failed to save IDF weights to {filepath}: {e}")
            raise

    def _save_summary_statistics(self, weights: IDFWeights, summary_path: str):
        """Save human-readable summary of IDF weights"""
        try:
            sorted_terms = sorted(weights.term_weights.items(), key=lambda x: x[1], reverse=True)
            avg_idf = sum(weights.term_weights.values()) / len(weights.term_weights)

            with open(summary_path, 'w') as f:
                f.write(f"IDF Weights Summary\n")
                f.write(f"==================\n\n")
                f.write(f"Calculation Date: {weights.calculation_date}\n")
                f.write(f"Total Documents: {weights.total_documents}\n")
                f.write(f"Vocabulary Size: {weights.vocabulary_size}\n")
                f.write(f"Average IDF: {avg_idf:.3f}\n")
                f.write(f"Corpus Hash: {weights.corpus_hash}\n\n")

                f.write(f"Top 50 Rare Terms (Highest IDF):\n")
                f.write(f"=================================\n")
                for i, (term, idf) in enumerate(sorted_terms[:50], 1):
                    f.write(f"{i:2d}. {term:30s} {idf:6.3f}\n")

                f.write(f"\nTop 50 Common Terms (Lowest IDF):\n")
                f.write(f"==================================\n")
                for i, (term, idf) in enumerate(sorted_terms[-50:], 1):
                    f.write(f"{i:2d}. {term:30s} {idf:6.3f}\n")

            self.logger.info(f"IDF summary saved to {summary_path}")

        except Exception as e:
            self.logger.warning(f"Failed to save IDF summary: {e}")

    def load_idf_weights(self, filepath: str) -> Optional[IDFWeights]:
        """
        Load IDF weights from file.

        Args:
            filepath: Path to the weights file

        Returns:
            IDFWeights object or None if loading failed
        """
        try:
            if not Path(filepath).exists():
                self.logger.info(f"IDF weights file not found: {filepath}")
                return None

            with open(filepath, 'r') as f:
                data = json.load(f)

            # Handle both old and new format
            if 'metadata' in data:
                # New format with metadata
                weights = IDFWeights(
                    term_weights=data['term_weights'],
                    total_documents=data['metadata']['total_documents'],
                    vocabulary_size=data['metadata']['vocabulary_size'],
                    calculation_date=data['metadata']['calculation_date'],
                    corpus_hash=data['metadata']['corpus_hash']
                )
            else:
                # Old format (backwards compatibility)
                weights = IDFWeights(
                    term_weights=data.get('term_weights', {}),
                    total_documents=data.get('total_documents', 0),
                    vocabulary_size=data.get('vocabulary_size', 0),
                    calculation_date=data.get('calculation_date', ''),
                    corpus_hash=data.get('corpus_hash', '')
                )

            self.logger.info(f"IDF weights loaded: {weights.vocabulary_size} terms from {weights.calculation_date}")

            # Validate the loaded weights
            if not self._validate_weights(weights):
                self.logger.warning("Loaded IDF weights failed validation")
                return None

            return weights

        except Exception as e:
            self.logger.error(f"Failed to load IDF weights from {filepath}: {e}")
            return None

    def _validate_weights(self, weights: IDFWeights) -> bool:
        """Validate loaded IDF weights for consistency"""
        try:
            # Check basic structure
            if not weights.term_weights or not isinstance(weights.term_weights, dict):
                return False

            # Check that all weights are valid numbers
            for term, weight in weights.term_weights.items():
                if not isinstance(weight, (int, float)) or math.isnan(weight) or math.isinf(weight):
                    self.logger.warning(f"Invalid weight for term '{term}': {weight}")
                    return False

            # Check vocabulary size consistency
            if len(weights.term_weights) != weights.vocabulary_size:
                self.logger.warning(
                    f"Vocabulary size mismatch: {len(weights.term_weights)} vs {weights.vocabulary_size}")
                return False

            return True

        except Exception as e:
            self.logger.error(f"IDF weights validation failed: {e}")
            return False

    def update_idf_weights(self, existing_weights: IDFWeights,
                           new_documents: List[str]) -> IDFWeights:
        """
        Update existing IDF weights with new documents.

        This allows incremental updates to the IDF weights without
        recalculating from the entire corpus.

        Args:
            existing_weights: Current IDF weights
            new_documents: New documents to incorporate

        Returns:
            Updated IDFWeights object
        """
        self.logger.info(f"Updating IDF weights with {len(new_documents)} new documents")

        # For simplicity, we recalculate with the new total
        # In a production system, you might want true incremental updates
        total_docs = existing_weights.total_documents + len(new_documents)

        # Get chess concepts
        chess_concepts = ChessVocabulary.get_chess_concepts()
        all_terms = []
        for category, terms in chess_concepts.items():
            all_terms.extend([term.lower() for term in terms])
        unique_terms = list(dict.fromkeys(all_terms))

        # Count terms in new documents
        new_term_counts = Counter()

        with tqdm(new_documents, desc="Analyzing new documents", unit="docs") as pbar:
            for document in new_documents:
                try:
                    doc_lower = document.lower()
                    doc_terms = set()

                    for term in unique_terms:
                        if term in doc_lower:
                            doc_terms.add(term)

                    for term in doc_terms:
                        new_term_counts[term] += 1

                    pbar.update(1)

                except Exception as e:
                    self.logger.warning(f"Error processing new document: {e}")
                    continue

        # Update term frequencies (this is a simplified approach)
        updated_weights = {}

        for term in unique_terms:
            # Estimate existing document frequency from IDF
            existing_idf = existing_weights.term_weights.get(term, 0)
            if existing_idf > 0:
                # Reverse calculate document frequency
                estimated_old_freq = math.exp(math.log(existing_weights.total_documents + 1) - existing_idf) - 1
            else:
                estimated_old_freq = 0

            # Add new document frequency
            new_freq = new_term_counts.get(term, 0)
            total_freq = estimated_old_freq + new_freq

            # Calculate new IDF
            if total_freq > 0:
                new_idf = math.log((total_docs + 1) / (total_freq + 1))
            else:
                new_idf = math.log(total_docs + 1)

            updated_weights[term] = new_idf

        # Create updated corpus hash
        sample_text = " ".join(new_documents[:10])  # Sample from new documents
        updated_hash = hashlib.md5(
            (existing_weights.corpus_hash + sample_text).encode()
        ).hexdigest()

        updated_idf_weights = IDFWeights(
            term_weights=updated_weights,
            total_documents=total_docs,
            vocabulary_size=len(updated_weights),
            calculation_date=datetime.now().isoformat(),
            corpus_hash=updated_hash
        )

        self.logger.info(f"IDF weights updated: {total_docs} total documents")
        return updated_idf_weights

    def analyze_term_importance(self, weights: IDFWeights,
                                category_weights: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """
        Analyze term importance patterns in the IDF weights.

        This provides insights into which types of chess terms are rare/common
        and can help optimize the semantic analysis.

        Args:
            weights: IDF weights to analyze
            category_weights: Optional category importance weights

        Returns:
            Dictionary with analysis results
        """
        chess_concepts = ChessVocabulary.get_chess_concepts()

        if category_weights is None:
            from ..core.constants import CategoryWeights
            category_weights = CategoryWeights.INSTRUCTIONAL_ANALYSIS_WEIGHTS

        # Analyze by category
        category_analysis = {}

        for category, terms in chess_concepts.items():
            category_terms = [term.lower() for term in terms]
            category_idfs = [weights.term_weights.get(term, 0) for term in category_terms]

            if category_idfs:
                category_analysis[category] = {
                    'term_count': len(category_terms),
                    'avg_idf': sum(category_idfs) / len(category_idfs),
                    'min_idf': min(category_idfs),
                    'max_idf': max(category_idfs),
                    'category_weight': category_weights.get(category, 1.0),
                    'weighted_importance': (sum(category_idfs) / len(category_idfs)) * category_weights.get(category,
                                                                                                            1.0)
                }

        # Overall statistics
        all_idfs = list(weights.term_weights.values())
        overall_stats = {
            'total_terms': len(all_idfs),
            'avg_idf': sum(all_idfs) / len(all_idfs),
            'min_idf': min(all_idfs),
            'max_idf': max(all_idfs),
            'std_idf': math.sqrt(sum((x - sum(all_idfs) / len(all_idfs)) ** 2 for x in all_idfs) / len(all_idfs))
        }

        # Find most/least important categories
        sorted_categories = sorted(
            category_analysis.items(),
            key=lambda x: x[1]['weighted_importance'],
            reverse=True
        )

        return {
            'overall_statistics': overall_stats,
            'category_analysis': category_analysis,
            'most_important_categories': [cat for cat, _ in sorted_categories[:5]],
            'least_important_categories': [cat for cat, _ in sorted_categories[-5:]],
            'calculation_metadata': {
                'total_documents': weights.total_documents,
                'vocabulary_size': weights.vocabulary_size,
                'calculation_date': weights.calculation_date
            }
        }