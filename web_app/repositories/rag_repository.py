"""
Repository for RAG (Retrieval-Augmented Generation) database operations
"""

import uuid

from sqlalchemy import delete, func, select, text

from web_app.database.models import ExtractionPrompt, Query, SourceText, TextCorpus
from web_app.repositories.base_repository import BaseRepository


class RAGRepository(BaseRepository):
    """Repository for RAG-related database operations"""

    def __init__(self, db_session=None):
        super().__init__(db_session)

    def create_corpus(self, name: str, description: str = "", **kwargs) -> TextCorpus:
        """Create a new text corpus"""
        def _create_corpus():
            corpus = TextCorpus(
                name=name,
                description=description,
                raw_content=kwargs.get('raw_content'),
                is_active=kwargs.get('is_active', True),
                chunk_size=kwargs.get('chunk_size', 1500),
                chunk_overlap=kwargs.get('chunk_overlap', 200),
                embedding_model=kwargs.get('embedding_model', 'nomic-embed-text'),
                query_chunk_limit=kwargs.get('query_chunk_limit', 20),
                processing_status=kwargs.get('processing_status', 'ready')
            )
            self.db_session.add(corpus)
            return corpus

        return self.safe_operation(_create_corpus, f"create corpus {name}")

    def get_active_corpus(self) -> TextCorpus | None:
        """Get the currently active corpus"""
        def _get_active_corpus():
            stmt = select(TextCorpus).filter_by(is_active=True)
            return self.db_session.execute(stmt).scalar_one_or_none()

        return self.safe_query(_get_active_corpus, "get active corpus")

    def get_all_corpora(self) -> list[TextCorpus]:
        """Get all text corpora"""
        def _get_all_corpora():
            stmt = select(TextCorpus).order_by(TextCorpus.created_at.desc())
            return self.db_session.execute(stmt).scalars().all()

        return self.safe_query(_get_all_corpora, "get all corpora")

    def get_corpus_by_id(self, corpus_id: str | uuid.UUID) -> TextCorpus | None:
        """Get corpus by ID"""
        if isinstance(corpus_id, str):
            corpus_id = uuid.UUID(corpus_id)

        return self.db_session.get(TextCorpus, corpus_id)

    def update_corpus_status(self, corpus_id: str | uuid.UUID, status: str, error: str = None) -> TextCorpus:
        """Update corpus processing status"""
        def _update_status():
            if isinstance(corpus_id, str):
                corpus_id_uuid = uuid.UUID(corpus_id)
            else:
                corpus_id_uuid = corpus_id

            corpus = self.db_session.get(TextCorpus, corpus_id_uuid)
            if not corpus:
                raise ValueError(f"Corpus not found: {corpus_id}")

            corpus.processing_status = status
            corpus.processing_error = error
            return corpus

        return self.safe_operation(_update_status, f"update corpus {corpus_id} status to {status}")

    def create_source_text(self, corpus_id: str | uuid.UUID, **kwargs) -> SourceText:
        """Create a source text record"""
        def _create_source_text():
            if isinstance(corpus_id, str):
                corpus_id_uuid = uuid.UUID(corpus_id)
            else:
                corpus_id_uuid = corpus_id

            source_text = SourceText(
                corpus_id=corpus_id_uuid,
                filename=kwargs.get('filename'),
                page_number=kwargs.get('page_number'),
                chunk_number=kwargs.get('chunk_number'),
                content=kwargs.get('content'),
                content_hash=kwargs.get('content_hash'),
                embedding=kwargs.get('embedding'),
                embedding_model=kwargs.get('embedding_model'),
                token_count=kwargs.get('token_count'),
                dm_codes=kwargs.get('dm_codes'),
                generation_number=kwargs.get('generation_number'),
                generation_text=kwargs.get('generation_text'),
                family_context=kwargs.get('family_context'),
                birth_years=kwargs.get('birth_years'),
                chunk_type=kwargs.get('chunk_type')
            )
            self.db_session.add(source_text)
            return source_text

        return self.safe_operation(_create_source_text, f"create source text for corpus {corpus_id}")

    def get_source_text_by_hash(self, corpus_id: str | uuid.UUID, content_hash: str) -> SourceText | None:
        """Check if source text with content hash already exists"""
        def _get_by_hash():
            if isinstance(corpus_id, str):
                corpus_id_uuid = uuid.UUID(corpus_id)
            else:
                corpus_id_uuid = corpus_id

            stmt = select(SourceText).filter_by(
                corpus_id=corpus_id_uuid,
                content_hash=content_hash
            )
            return self.db_session.execute(stmt).scalar_one_or_none()

        return self.safe_query(_get_by_hash, f"get source text by hash for corpus {corpus_id}")

    def create_query(self, **kwargs) -> Query:
        """Create a query record"""
        def _create_query():
            # Convert string UUIDs to UUID objects if needed
            corpus_id = kwargs.get('corpus_id')
            if isinstance(corpus_id, str):
                kwargs['corpus_id'] = uuid.UUID(corpus_id)

            conversation_id = kwargs.get('conversation_id')
            if isinstance(conversation_id, str):
                kwargs['conversation_id'] = uuid.UUID(conversation_id)

            query = Query(**kwargs)
            self.db_session.add(query)
            return query

        return self.safe_operation(_create_query, "create query")

    def delete_corpus(self, corpus_id: str | uuid.UUID) -> dict:
        """Delete a corpus and all related data"""
        def _delete_corpus():
            if isinstance(corpus_id, str):
                corpus_id_uuid = uuid.UUID(corpus_id)
            else:
                corpus_id_uuid = corpus_id

            corpus = self.db_session.get(TextCorpus, corpus_id_uuid)
            if not corpus:
                raise ValueError(f"Corpus not found: {corpus_id}")

            corpus_name = corpus.name

            # Get counts before deletion
            chunk_count = self.db_session.execute(
                select(func.count(SourceText.id)).filter_by(corpus_id=corpus_id_uuid)
            ).scalar()

            query_count = self.db_session.execute(
                select(func.count(Query.id)).filter_by(corpus_id=corpus_id_uuid)
            ).scalar()

            # Delete related records (cascading should handle this, but being explicit)
            if query_count > 0:
                self.db_session.execute(
                    delete(Query).where(Query.corpus_id == corpus_id_uuid)
                )

            if chunk_count > 0:
                self.db_session.execute(
                    delete(SourceText).where(SourceText.corpus_id == corpus_id_uuid)
                )

            # Delete the corpus
            self.db_session.delete(corpus)

            return {
                'corpus_name': corpus_name,
                'deleted_chunks': chunk_count,
                'deleted_queries': query_count
            }

        return self.safe_operation(_delete_corpus, f"delete corpus {corpus_id}")

    def get_corpus_stats(self, corpus_id: str | uuid.UUID) -> dict:
        """Get statistics for a corpus"""
        def _get_stats():
            if isinstance(corpus_id, str):
                corpus_id_uuid = uuid.UUID(corpus_id)
            else:
                corpus_id_uuid = corpus_id

            chunk_count = self.db_session.execute(
                select(func.count(SourceText.id)).filter_by(corpus_id=corpus_id_uuid)
            ).scalar()

            unique_files = self.db_session.execute(
                select(func.count(func.distinct(SourceText.filename))).filter_by(corpus_id=corpus_id_uuid)
            ).scalar()

            return {
                'chunk_count': chunk_count,
                'unique_files': unique_files
            }

        return self.safe_query(_get_stats, f"get corpus stats for {corpus_id}")

    def get_prompt_by_id(self, prompt_id: str | uuid.UUID, expected_type: str = None) -> ExtractionPrompt:
        """Get a prompt by ID, optionally validate type"""
        def _get_prompt():
            if isinstance(prompt_id, str):
                prompt_id_uuid = uuid.UUID(prompt_id)
            else:
                prompt_id_uuid = prompt_id

            prompt = self.db_session.get(ExtractionPrompt, prompt_id_uuid)
            if not prompt:
                raise ValueError(f"Prompt not found: {prompt_id}")

            if expected_type and prompt.prompt_type != expected_type:
                raise ValueError(f"Prompt {prompt_id} is type '{prompt.prompt_type}', expected '{expected_type}'")

            return prompt

        return self.safe_query(_get_prompt, f"get prompt {prompt_id}")

    def get_all_prompts(self, prompt_type: str = None) -> list[ExtractionPrompt]:
        """Get all prompts ordered by creation date, optionally filtered by type"""
        def _get_all_prompts():
            stmt = select(ExtractionPrompt).order_by(ExtractionPrompt.created_at.desc())
            if prompt_type:
                stmt = stmt.filter_by(prompt_type=prompt_type)
            return self.db_session.execute(stmt).scalars().all()

        return self.safe_query(_get_all_prompts, f"get all prompts (type: {prompt_type})")

    def create_prompt(self, name: str, prompt_text: str, prompt_type: str = 'extraction', description: str = "", template_variables: list = None) -> ExtractionPrompt:
        """Create a new prompt"""
        def _create_prompt():
            prompt = ExtractionPrompt(
                name=name,
                prompt_text=prompt_text,
                prompt_type=prompt_type,
                description=description,
                template_variables=template_variables or []
            )
            self.db_session.add(prompt)
            return prompt

        return self.safe_operation(_create_prompt, f"create prompt {name}")

    def update_prompt(self, prompt_id: str | uuid.UUID, name: str = None, prompt_text: str = None, description: str = None) -> ExtractionPrompt:
        """Update an existing prompt"""
        def _update_prompt():
            if isinstance(prompt_id, str):
                prompt_id_uuid = uuid.UUID(prompt_id)
            else:
                prompt_id_uuid = prompt_id

            prompt = self.db_session.get(ExtractionPrompt, prompt_id_uuid)
            if not prompt:
                raise ValueError(f"Prompt not found: {prompt_id}")

            if name is not None:
                prompt.name = name
            if prompt_text is not None:
                prompt.prompt_text = prompt_text
            if description is not None:
                prompt.description = description

            return prompt

        return self.safe_operation(_update_prompt, f"update prompt {prompt_id}")

    def delete_prompt(self, prompt_id: str | uuid.UUID) -> dict:
        """Delete a prompt"""
        def _delete_prompt():
            if isinstance(prompt_id, str):
                prompt_id_uuid = uuid.UUID(prompt_id)
            else:
                prompt_id_uuid = prompt_id

            prompt = self.db_session.get(ExtractionPrompt, prompt_id_uuid)
            if not prompt:
                raise ValueError(f"Prompt not found: {prompt_id}")

            prompt_name = prompt.name
            prompt_type = prompt.prompt_type
            self.db_session.delete(prompt)

            return {
                'prompt_name': prompt_name,
                'prompt_type': prompt_type
            }

        return self.safe_operation(_delete_prompt, f"delete prompt {prompt_id}")

    def get_prompt_by_name_and_type(self, name: str, prompt_type: str) -> ExtractionPrompt | None:
        """Get a prompt by name and type"""
        def _get_by_name_type():
            stmt = select(ExtractionPrompt).filter_by(name=name, prompt_type=prompt_type)
            return self.db_session.execute(stmt).scalar_one_or_none()

        return self.safe_query(_get_by_name_type, f"get prompt by name {name} and type {prompt_type}")

    def find_similar(self, query_embedding, corpus_id: str | uuid.UUID = None, limit: int = 5, similarity_threshold: float = 0.7) -> list[tuple[SourceText, float]]:
        """Find text chunks similar to the query embedding using cosine similarity"""
        from sqlalchemy import text

        def _find_similar():
            # Convert numpy array to list for pgvector compatibility
            if hasattr(query_embedding, 'tolist'):
                query_embedding_list = query_embedding.tolist()
            elif isinstance(query_embedding, list):
                query_embedding_list = query_embedding
            else:
                query_embedding_list = list(query_embedding)

            # Convert embedding to vector string for PostgreSQL
            vector_str = '[' + ','.join(map(str, query_embedding_list)) + ']'

            if isinstance(corpus_id, str):
                corpus_id_uuid = uuid.UUID(corpus_id)
            else:
                corpus_id_uuid = corpus_id

            # Build query with optional corpus filter
            where_clause = "WHERE embedding IS NOT NULL"
            params = {
                'limit': limit,
                'similarity_threshold': similarity_threshold
            }

            if corpus_id_uuid:
                where_clause += " AND corpus_id = :corpus_id"
                params['corpus_id'] = corpus_id_uuid

            query = text(f"""
                SELECT *, (1 - (embedding <=> '{vector_str}'::vector)) as similarity
                FROM source_texts
                {where_clause}
                AND (1 - (embedding <=> '{vector_str}'::vector)) >= :similarity_threshold
                ORDER BY embedding <=> '{vector_str}'::vector
                LIMIT :limit
            """)

            result = self.db_session.execute(query, params)

            # Convert results to SourceText objects with similarity scores
            results = []
            for row in result:
                source_text = SourceText(
                    id=row.id,
                    corpus_id=row.corpus_id,
                    filename=row.filename,
                    page_number=row.page_number,
                    chunk_number=row.chunk_number,
                    content=row.content,
                    content_hash=row.content_hash,
                    embedding=row.embedding,
                    embedding_model=row.embedding_model,
                    token_count=row.token_count,
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                    content_tsvector=row.content_tsvector,
                    dm_codes=row.dm_codes,
                    generation_number=row.generation_number,
                    generation_text=row.generation_text,
                    family_context=row.family_context,
                    birth_years=row.birth_years,
                    chunk_type=row.chunk_type
                )
                results.append((source_text, float(row.similarity)))

            return results

        return self.safe_query(_find_similar, f"find similar chunks for corpus {corpus_id}")

    def get_conversation(self, conversation_id: str | uuid.UUID) -> list[Query]:
        """Get all queries in a conversation, ordered by sequence"""
        def _get_conversation():
            if isinstance(conversation_id, str):
                conversation_id_uuid = uuid.UUID(conversation_id)
            else:
                conversation_id_uuid = conversation_id

            stmt = select(Query).filter_by(
                conversation_id=conversation_id_uuid
            ).order_by(Query.message_sequence)
            return self.db_session.execute(stmt).scalars().all()

        return self.safe_query(_get_conversation, f"get conversation {conversation_id}")

    def start_new_conversation(self, corpus_id: str | uuid.UUID) -> uuid.UUID:
        """Start a new conversation and return the conversation_id"""
        return uuid.uuid4()

    def hybrid_search(self, query_text: str, corpus_id: str | uuid.UUID, query_embedding: list[float],
                     query_dm_codes: list[str], vec_limit: int = 25, trgm_limit: int = 20,
                     phon_limit: int = 40, limit: int = 5) -> list[tuple]:
        """Execute hybrid search query using RRF combining vector, trigram, full-text, and phonetic search"""

        def _hybrid_search():
            if isinstance(corpus_id, str):
                corpus_id_uuid = uuid.UUID(corpus_id)
            else:
                corpus_id_uuid = corpus_id

            # Convert embedding to vector string for PostgreSQL
            if hasattr(query_embedding, 'tolist'):
                query_embedding_list = query_embedding.tolist()
            elif isinstance(query_embedding, list):
                query_embedding_list = query_embedding
            else:
                query_embedding_list = list(query_embedding)
            vector_str = '[' + ','.join(map(str, query_embedding_list)) + ']'

            # Convert DM codes array to PostgreSQL array literal
            if query_dm_codes:
                dm_codes_str = "ARRAY[" + ",".join(f"'{code}'" for code in query_dm_codes) + "]"
            else:
                dm_codes_str = "ARRAY[]::varchar[]"

            # Execute hybrid search query using RRF
            hybrid_query = text(f"""
                WITH
                params AS (
                  SELECT
                    '{vector_str}'::vector AS q_vec,
                    plainto_tsquery('dutch', :query_text) AS q_ts,
                    {dm_codes_str} AS q_dm
                ),

                vec AS (
                  SELECT id,
                         row_number() OVER () AS vec_rank
                  FROM   source_texts, params
                  WHERE  corpus_id = :corpus_id
                    AND  embedding IS NOT NULL
                  ORDER  BY embedding <=> q_vec
                  LIMIT  :vec_limit
                ),

                trgm AS (
                  SELECT id,
                         row_number() OVER (ORDER BY similarity(content, :query_text) DESC) AS tg_rank
                  FROM   source_texts
                  WHERE  corpus_id = :corpus_id
                    AND  content % :query_text
                  LIMIT  :trgm_limit
                ),

                fts AS (
                  SELECT id,
                         row_number() OVER (ORDER BY ts_rank(content_tsvector, q_ts) DESC) AS fts_rank
                  FROM   source_texts, params
                  WHERE  corpus_id = :corpus_id
                    AND  content_tsvector @@ q_ts
                  LIMIT  :trgm_limit
                ),

                phon AS (
                  SELECT id,
                         row_number() OVER () AS ph_rank
                  FROM   source_texts, params
                  WHERE  corpus_id = :corpus_id
                    AND  dm_codes && q_dm::varchar[]
                    AND  array_length(q_dm, 1) > 0
                  LIMIT  :phon_limit
                ),

                rrf AS (
                  SELECT id, 1.0/(60+vec_rank) AS score FROM vec
                  UNION ALL
                  SELECT id, 1.0/(60+tg_rank) AS score FROM trgm
                  UNION ALL
                  SELECT id, 1.0/(60+fts_rank) AS score FROM fts
                  UNION ALL
                  SELECT id, 1.0/(80+ph_rank) AS score FROM phon
                )

                SELECT st.id, st.corpus_id, st.filename, st.page_number, st.chunk_number,
                       st.content, st.content_hash, st.embedding, st.embedding_model,
                       st.token_count, st.created_at, st.updated_at, st.content_tsvector,
                       st.dm_codes, st.generation_number, st.generation_text, st.family_context,
                       st.birth_years, st.chunk_type, SUM(rrf.score) as combined_score
                FROM   rrf
                JOIN   source_texts st ON rrf.id = st.id
                GROUP  BY st.id, st.corpus_id, st.filename, st.page_number, st.chunk_number,
                          st.content, st.content_hash, st.embedding, st.embedding_model,
                          st.token_count, st.created_at, st.updated_at, st.content_tsvector,
                          st.dm_codes, st.generation_number, st.generation_text, st.family_context,
                          st.birth_years, st.chunk_type
                ORDER  BY SUM(rrf.score) DESC
                LIMIT  :limit
            """)

            # Execute the query
            result = self.db_session.execute(hybrid_query, {
                'query_text': query_text,
                'corpus_id': corpus_id_uuid,
                'vec_limit': vec_limit,
                'trgm_limit': trgm_limit,
                'phon_limit': phon_limit,
                'limit': limit
            })

            rows = result.fetchall()

            # Convert results to SourceText objects with scores
            results = []
            for row in rows:
                source_text = SourceText(
                    id=row.id,
                    corpus_id=row.corpus_id,
                    filename=row.filename,
                    page_number=row.page_number,
                    chunk_number=row.chunk_number,
                    content=row.content,
                    content_hash=row.content_hash,
                    embedding=row.embedding,
                    embedding_model=row.embedding_model,
                    token_count=row.token_count,
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                    content_tsvector=row.content_tsvector,
                    dm_codes=row.dm_codes,
                    generation_number=row.generation_number,
                    generation_text=row.generation_text,
                    family_context=row.family_context,
                    birth_years=row.birth_years,
                    chunk_type=row.chunk_type
                )
                results.append((source_text, float(row.combined_score)))

            return results

        return self.safe_query(_hybrid_search, f"hybrid search for corpus {corpus_id}")
