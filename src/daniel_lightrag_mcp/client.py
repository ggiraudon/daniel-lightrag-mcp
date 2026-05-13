"""
LightRAG API client for MCP server integration.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, AsyncGenerator
import httpx
from .models import (
    # Request models
    InsertTextRequest, InsertTextsRequest, QueryRequest, EntityUpdateRequest,
    RelationUpdateRequest, DeleteDocRequest, DeleteEntityRequest, DeleteRelationRequest,
    DocumentsRequest, ClearCacheRequest, EntityExistsRequest,
    # Response models
    InsertResponse, ScanResponse, UploadResponse, DocumentsResponse, PaginatedDocsResponse,
    DeleteDocByIdResponse, ClearDocumentsResponse, PipelineStatusResponse, TrackStatusResponse,
    StatusCountsResponse, ClearCacheResponse, DeletionResult, QueryResponse, GraphResponse,
    LabelsResponse, EntityExistsResponse, EntityUpdateResponse, RelationUpdateResponse,
    HealthResponse, TextDocument,
    # Graph traversal models
    RandomEntityResponse, FindPathResponse, RandomDisconnectResponse,
    # Graph exploration models
    EntityNeighborsResponse, MostConnectedEntity, MostConnectedResponse,
    GraphStatsResponse, SimilarEntity, SimilarEntitiesResponse,
    CommonNeighborsResponse, IsolatedEntitiesResponse,
    BridgeEntity, BridgeEntitiesResponse, LabelPopularityResponse,
    GhostNode, GhostNodesResponse
)


# Custom Exception Hierarchy
class LightRAGError(Exception):
    """Base exception for LightRAG client errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_data = response_data or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/serialization."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "status_code": self.status_code,
            "response_data": self.response_data
        }


class LightRAGConnectionError(LightRAGError):
    """Exception for connection-related errors."""
    pass


class LightRAGAuthError(LightRAGError):
    """Exception for authentication failures."""
    pass


class LightRAGValidationError(LightRAGError):
    """Exception for input validation errors."""
    pass


class LightRAGAPIError(LightRAGError):
    """Exception for API-specific errors."""
    pass


class LightRAGTimeoutError(LightRAGError):
    """Exception for request timeout errors."""
    pass


class LightRAGServerError(LightRAGError):
    """Exception for server-side errors (5xx status codes)."""
    pass


class LightRAGClient:
    """Client for interacting with LightRAG API."""
    
    def __init__(self, base_url: str = "http://localhost:9621", api_key: Optional[str] = None, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
        
        headers = {}
        if api_key:
            headers["X-API-Key"] = api_key
            
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers=headers
        )
        
        self.logger.info(f"Initialized LightRAG client with base_url: {self.base_url}")
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    def _map_http_error(self, status_code: int, response_text: str, response_data: Optional[Dict[str, Any]] = None) -> LightRAGError:
        """Map HTTP status codes to appropriate exception types."""
        error_message = f"HTTP {status_code}: {response_text}"
        
        # Try to parse response data for more detailed error information
        parsed_data = response_data or {}
        if response_text:
            try:
                parsed_data = json.loads(response_text)
                if isinstance(parsed_data, dict) and "detail" in parsed_data:
                    error_message = f"HTTP {status_code}: {parsed_data['detail']}"
                elif isinstance(parsed_data, dict) and "message" in parsed_data:
                    error_message = f"HTTP {status_code}: {parsed_data['message']}"
            except json.JSONDecodeError:
                pass
        
        # Map status codes to specific exception types
        if status_code == 400:
            return LightRAGValidationError(f"Bad Request: {error_message}", status_code, parsed_data)
        elif status_code == 401:
            return LightRAGAuthError(f"Unauthorized: {error_message}", status_code, parsed_data)
        elif status_code == 403:
            return LightRAGAuthError(f"Forbidden: {error_message}", status_code, parsed_data)
        elif status_code == 404:
            return LightRAGAPIError(f"Not Found: {error_message}", status_code, parsed_data)
        elif status_code == 408:
            return LightRAGTimeoutError(f"Request Timeout: {error_message}", status_code, parsed_data)
        elif status_code == 422:
            return LightRAGValidationError(f"Validation Error: {error_message}", status_code, parsed_data)
        elif status_code == 429:
            return LightRAGAPIError(f"Rate Limited: {error_message}", status_code, parsed_data)
        elif 500 <= status_code < 600:
            return LightRAGServerError(f"Server Error: {error_message}", status_code, parsed_data)
        else:
            return LightRAGAPIError(error_message, status_code, parsed_data)
    
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make HTTP request to LightRAG API."""
        url = f"{self.base_url}{endpoint}"
        
        # Log request details
        self.logger.debug(f"Making {method} request to {url}")
        if data:
            self.logger.debug(f"Request data: {json.dumps(data, indent=2)}")
        if params:
            self.logger.debug(f"Request params: {params}")
        
        try:
            if method.upper() == "GET":
                response = await self.client.get(url, params=params)
            elif method.upper() == "POST":
                if files:
                    response = await self.client.post(url, data=data, files=files)
                else:
                    response = await self.client.post(url, json=data)
            elif method.upper() == "DELETE":
                if data:
                    response = await self.client.request("DELETE", url, json=data)
                else:
                    response = await self.client.delete(url)
            else:
                error_msg = f"Unsupported HTTP method: {method}"
                self.logger.error(error_msg)
                raise LightRAGError(error_msg)
            
            # Log response details
            self.logger.debug(f"Response status: {response.status_code}")
            try:
                self.logger.debug(f"Response headers: {dict(response.headers)}")
            except (TypeError, AttributeError):
                # Handle mock objects that don't have proper headers
                self.logger.debug("Response headers: <mock headers>")
            
            response.raise_for_status()
            
            try:
                response_data = response.json()
                self.logger.debug(f"Response data: {json.dumps(response_data, indent=2)}")
                self.logger.info(f"Successfully completed {method} request to {endpoint}")
                return response_data
            except json.JSONDecodeError as json_err:
                self.logger.error(f"Failed to parse JSON response: {json_err}")
                self.logger.error(f"Raw response text: {response.text}")
                raise LightRAGAPIError(f"Invalid JSON response from server: {str(json_err)}")
            
        except httpx.HTTPStatusError as e:
            self.logger.error(f"HTTP error {e.response.status_code} for {method} {url}: {e.response.text}")
            raise self._map_http_error(e.response.status_code, e.response.text)
        except httpx.ConnectError as e:
            error_msg = f"Connection failed to {url}: {str(e)}"
            self.logger.error(error_msg)
            raise LightRAGConnectionError(error_msg)
        except httpx.TimeoutException as e:
            error_msg = f"Request timeout for {method} {url}: {str(e)}"
            self.logger.error(error_msg)
            raise LightRAGTimeoutError(error_msg)
        except httpx.RequestError as e:
            error_msg = f"Request failed for {method} {url}: {str(e)}"
            self.logger.error(error_msg)
            raise LightRAGConnectionError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error during {method} request to {url}: {str(e)}"
            self.logger.error(error_msg)
            raise LightRAGError(error_msg)
    
    async def _stream_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """Make streaming HTTP request to LightRAG API."""
        url = f"{self.base_url}{endpoint}"
        
        # Log streaming request details
        self.logger.debug(f"Making streaming {method} request to {url}")
        if data:
            self.logger.debug(f"Streaming request data: {json.dumps(data, indent=2)}")
        
        try:
            async with self.client.stream(method, url, json=data) as response:
                self.logger.debug(f"Streaming response status: {response.status_code}")
                response.raise_for_status()
                
                chunk_count = 0
                async for chunk in response.aiter_text():
                    if chunk.strip():
                        chunk_count += 1
                        self.logger.debug(f"Received streaming chunk {chunk_count}: {len(chunk)} characters")
                        yield chunk
                
                self.logger.info(f"Successfully completed streaming {method} request to {endpoint}, received {chunk_count} chunks")
                        
        except httpx.HTTPStatusError as e:
            self.logger.error(f"HTTP error {e.response.status_code} for streaming {method} {url}: {e.response.text}")
            raise self._map_http_error(e.response.status_code, e.response.text)
        except httpx.ConnectError as e:
            error_msg = f"Connection failed for streaming request to {url}: {str(e)}"
            self.logger.error(error_msg)
            raise LightRAGConnectionError(error_msg)
        except httpx.TimeoutException as e:
            error_msg = f"Request timeout for streaming {method} {url}: {str(e)}"
            self.logger.error(error_msg)
            raise LightRAGTimeoutError(error_msg)
        except httpx.RequestError as e:
            error_msg = f"Request failed for streaming {method} {url}: {str(e)}"
            self.logger.error(error_msg)
            raise LightRAGConnectionError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error during streaming {method} request to {url}: {str(e)}"
            self.logger.error(error_msg)
            raise LightRAGError(error_msg)
    
    # Document Management Methods (8 methods)
    
    async def insert_text(self, text: str, title: Optional[str] = None) -> InsertResponse:
        """Insert text content into LightRAG."""
        self.logger.info(f"Inserting text document with title: {title}")
        try:
            # Use title as file_source if provided, otherwise use generic name
            file_source = f"{title}.txt" if title else "text_input.txt"
            request_data = InsertTextRequest(text=text, file_source=file_source)
            response_data = await self._make_request("POST", "/documents/text", request_data.model_dump())
            result = InsertResponse(**response_data)
            self.logger.info(f"Successfully inserted text document with ID: {result.id}")
            return result
        except Exception as e:
            self.logger.error(f"Failed to insert text document: {str(e)}")
            if isinstance(e, LightRAGError):
                raise
            # Handle Pydantic validation errors
            if hasattr(e, 'errors') and callable(getattr(e, 'errors')):
                raise LightRAGValidationError(f"Request validation failed: {str(e)}")
            raise LightRAGError(f"Text insertion failed: {str(e)}")
    
    async def insert_texts(self, texts: List[TextDocument]) -> InsertResponse:
        """Insert multiple text documents into LightRAG."""
        # Convert TextDocument objects to strings (content only)
        text_strings = []
        for doc in texts:
            if isinstance(doc, dict):
                # Handle dict input from tests
                text_strings.append(doc.get('content', str(doc)))
            elif hasattr(doc, 'content'):
                # Handle TextDocument objects
                text_strings.append(doc.content)
            else:
                # Handle string input
                text_strings.append(str(doc))
        
        # Create file sources for each text (use generic names to avoid null file_path)
        file_sources = [f"text_input_{i+1}.txt" for i in range(len(text_strings))]
        
        request_data = InsertTextsRequest(texts=text_strings, file_sources=file_sources)
        response_data = await self._make_request("POST", "/documents/texts", request_data.model_dump())
        return InsertResponse(**response_data)
    
    async def upload_document(self, file_path: str) -> UploadResponse:
        """Upload a document file to LightRAG."""
        self.logger.info(f"Uploading document file: {file_path}")
        try:
            # Validate file exists and is readable
            import os
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File does not exist: {file_path}")
            if not os.access(file_path, os.R_OK):
                raise PermissionError(f"File is not readable: {file_path}")
            
            file_size = os.path.getsize(file_path)
            self.logger.debug(f"File size: {file_size} bytes")
            
            with open(file_path, 'rb') as f:
                files = {"file": (os.path.basename(file_path), f, "application/octet-stream")}
                response_data = await self._make_request("POST", "/documents/upload", files=files)
                result = UploadResponse(**response_data)
                self.logger.info(f"Successfully uploaded document: {file_path} ({file_size} bytes) - Track ID: {result.track_id}")
                return result
        except FileNotFoundError as e:
            error_msg = f"File not found: {file_path}"
            self.logger.error(error_msg)
            raise LightRAGValidationError(error_msg)
        except PermissionError as e:
            error_msg = f"Permission denied accessing file: {file_path}"
            self.logger.error(error_msg)
            raise LightRAGValidationError(error_msg)
        except Exception as e:
            error_msg = f"Failed to upload file {file_path}: {str(e)}"
            self.logger.error(error_msg)
            if isinstance(e, LightRAGError):
                raise
            raise LightRAGError(error_msg)
    
    async def scan_documents(self) -> ScanResponse:
        """Scan for new documents in LightRAG."""
        response_data = await self._make_request("POST", "/documents/scan")
        return ScanResponse(**response_data)
    
    async def get_documents(self) -> DocumentsResponse:
        """Retrieve all documents from LightRAG."""
        response_data = await self._make_request("GET", "/documents")
        return DocumentsResponse(**response_data)
    
    async def get_documents_paginated(self, page: int = 1, page_size: int = 10, status_filter: Optional[str] = None) -> PaginatedDocsResponse:
        """Retrieve documents with pagination from LightRAG."""
        request_data = DocumentsRequest(page=page, page_size=page_size, status_filter=status_filter)
        response_data = await self._make_request("POST", "/documents/paginated", request_data.model_dump())
        return PaginatedDocsResponse(**response_data)
    
    async def delete_document(self, document_id: str) -> DeleteDocByIdResponse:
        """Delete a document by ID from LightRAG."""
        request_data = DeleteDocRequest(doc_ids=[document_id])
        response_data = await self._make_request("DELETE", "/documents/delete_document", request_data.model_dump())
        return DeleteDocByIdResponse(**response_data)
    
    async def clear_documents(self) -> ClearDocumentsResponse:
        """Clear all documents from LightRAG."""
        response_data = await self._make_request("DELETE", "/documents")
        return ClearDocumentsResponse(**response_data)
    
    # Query Methods (2 methods)
    
    async def query_text(self, query: str, mode: str = "hybrid", only_need_context: bool = False) -> QueryResponse:
        """Query LightRAG with text."""
        self.logger.info(f"Querying text with mode '{mode}': {query[:100]}{'...' if len(query) > 100 else ''}")
        
        # Validate query parameters
        if not query or not query.strip():
            raise LightRAGValidationError("Query cannot be empty")
        
        valid_modes = ["naive", "local", "global", "hybrid"]
        if mode not in valid_modes:
            raise LightRAGValidationError(f"Invalid query mode '{mode}'. Must be one of: {valid_modes}")
        
        try:
            request_data = QueryRequest(query=query, mode=mode, only_need_context=only_need_context)
            response_data = await self._make_request("POST", "/query", request_data.model_dump())
            result = QueryResponse(**response_data)
            
            result_count = len(result.results) if hasattr(result, 'results') and result.results else 0
            self.logger.info(f"Query completed successfully, returned {result_count} results")
            return result
        except Exception as e:
            self.logger.error(f"Query failed for mode '{mode}': {str(e)}")
            if isinstance(e, LightRAGError):
                raise
            raise LightRAGError(f"Query operation failed: {str(e)}")
    
    async def query_text_stream(self, query: str, mode: str = "hybrid", only_need_context: bool = False) -> AsyncGenerator[str, None]:
        """Stream query results from LightRAG."""
        # Validate query parameters
        if not query or not query.strip():
            raise LightRAGValidationError("Query cannot be empty")
        
        valid_modes = ["naive", "local", "global", "hybrid"]
        if mode not in valid_modes:
            raise LightRAGValidationError(f"Invalid query mode '{mode}'. Must be one of: {valid_modes}")
        
        self.logger.info(f"Starting streaming query with mode '{mode}': {query[:100]}{'...' if len(query) > 100 else ''}")
        
        try:
            request_data = QueryRequest(query=query, mode=mode, only_need_context=only_need_context, stream=True)
            async for chunk in self._stream_request("POST", "/query/stream", request_data.model_dump()):
                yield chunk
        except Exception as e:
            self.logger.error(f"Streaming query failed for mode '{mode}': {str(e)}")
            if isinstance(e, LightRAGError):
                raise
            raise LightRAGError(f"Streaming query operation failed: {str(e)}")
    
    # Knowledge Graph Methods (8 methods)
    
    async def get_knowledge_graph(self, label: str = "*", max_depth: Optional[int] = None, max_nodes: Optional[int] = None) -> GraphResponse:
        """Retrieve the knowledge graph from LightRAG."""
        params = {"label": label}
        if max_depth is not None:
            params["max_depth"] = max_depth
        if max_nodes is not None:
            params["max_nodes"] = max_nodes
        response_data = await self._make_request("GET", "/graphs", params=params)
        return GraphResponse(**response_data)
    
    async def get_graph_labels(self) -> LabelsResponse:
        """Get labels for entities and relations in the knowledge graph."""
        response_data = await self._make_request("GET", "/graph/label/list")
        # Server returns a list, but our model expects a dict with labels field
        if isinstance(response_data, list):
            response_data = {"labels": response_data}
        return LabelsResponse(**response_data)
    
    async def check_entity_exists(self, entity_name: str) -> EntityExistsResponse:
        """Check if an entity exists in the knowledge graph."""
        params = {"name": entity_name}
        response_data = await self._make_request("GET", "/graph/entity/exists", params=params)
        return EntityExistsResponse(**response_data)
    
    async def update_entity(self, entity_id: str, properties: Dict[str, Any], entity_name: Optional[str] = None) -> EntityUpdateResponse:
        """Update an entity in the knowledge graph."""
        # Use entity_id as entity_name if not provided
        if entity_name is None:
            entity_name = entity_id
        request_data = EntityUpdateRequest(entity_id=entity_id, entity_name=entity_name, updated_data=properties)
        response_data = await self._make_request("POST", "/graph/entity/edit", request_data.model_dump())
        return EntityUpdateResponse(**response_data)
    
    # async def update_relation(self, relation_id: str, properties: Dict[str, Any], source_id: str = "unknown", target_id: str = "unknown") -> RelationUpdateResponse:
    #     """Update a relation in the knowledge graph."""
    #     request_data = RelationUpdateRequest(relation_id=relation_id, source_id=source_id, target_id=target_id, updated_data=properties)
    #     response_data = await self._make_request("POST", "/graph/relation/edit", request_data.model_dump())
    #     return RelationUpdateResponse(**response_data)

    async def update_relation(self, source_id: str, target_id: str, updated_data: Dict[str, Any]) -> RelationUpdateResponse:
        """Update a relation in the knowledge graph."""
        request_data = RelationUpdateRequest(
            source_id=source_id,
            target_id=target_id,
            updated_data=updated_data
        )
        response_data = await self._make_request("POST", "/graph/relation/edit", request_data.model_dump())
        return RelationUpdateResponse(**response_data)
    
    async def delete_entity(self, entity_id: str, entity_name: Optional[str] = None) -> DeletionResult:
        """Delete an entity from the knowledge graph."""
        # Use entity_id as entity_name if not provided
        if entity_name is None:
            entity_name = entity_id
        request_data = DeleteEntityRequest(entity_id=entity_id, entity_name=entity_name)
        response_data = await self._make_request("DELETE", "/documents/delete_entity", request_data.model_dump())
        return DeletionResult(**response_data)
    
    async def delete_relation(self, relation_id: str, source_entity: str = "unknown", target_entity: str = "unknown") -> DeletionResult:
        """Delete a relation from the knowledge graph."""
        request_data = DeleteRelationRequest(relation_id=relation_id, source_entity=source_entity, target_entity=target_entity)
        response_data = await self._make_request("DELETE", "/documents/delete_relation", request_data.model_dump())
        return DeletionResult(**response_data)
    
    # Knowledge Graph Traversal Methods (3 methods)
    
    async def get_random_entity(self) -> "RandomEntityResponse":
        """Get a random entity from the knowledge graph."""
        import random
        
        graph = await self.get_knowledge_graph(label="*", max_nodes=2000)
        nodes = graph.nodes
        if not nodes:
            raise LightRAGAPIError("No entities found in the knowledge graph")
        
        entity = random.choice(nodes)
        return RandomEntityResponse(entity=entity)
    
    async def find_path(self, source_entity: str, target_entity: str, max_depth: int = 10) -> "FindPathResponse":
        """Find a path between two entities in the knowledge graph using BFS on the subgraph."""
        from collections import deque
        
        # Fetch subgraph centered on source_entity with specified depth
        graph = await self.get_knowledge_graph(label=source_entity, max_depth=max_depth, max_nodes=2000)
        nodes = graph.nodes
        edges = graph.edges
        
        node_ids = {n.get('id', ''): n for n in nodes}
        # Also index by entity name (some APIs use 'entity_name' or 'name')
        id_by_name = {}
        for n in nodes:
            for key in ('entity_name', 'name', 'label'):
                val = n.get(key)
                if val:
                    id_by_name[val] = n.get('id', '')
        
        # Resolve source and target to node IDs
        def resolve_node_id(identifier: str) -> Optional[str]:
            if identifier in node_ids:
                return identifier
            if identifier in id_by_name:
                return id_by_name[identifier]
            # Try case-insensitive match
            lower = identifier.lower()
            for nid, node in node_ids.items():
                for key in ('entity_name', 'name', 'label', 'id'):
                    if str(node.get(key, '')).lower() == lower:
                        return nid
            return None
        
        src_id = resolve_node_id(source_entity)
        tgt_id = resolve_node_id(target_entity)
        
        if src_id is None:
            raise LightRAGAPIError(f"Source entity '{source_entity}' not found in the knowledge graph")
        if tgt_id is None:
            raise LightRAGAPIError(f"Target entity '{target_entity}' not found in the knowledge graph")
        
        if src_id == tgt_id:
            return FindPathResponse(found=True, path=[src_id], path_length=0, entities=[node_ids[src_id]])
        
        # Build adjacency list
        adj = {nid: [] for nid in node_ids}
        for edge in edges:
            src = edge.get('source_id') or edge.get('source')
            tgt = edge.get('target_id') or edge.get('target')
            if src in adj and tgt in adj:
                adj[src].append(tgt)
                adj[tgt].append(src)
        
        # BFS
        visited = {src_id}
        parent = {src_id: None}
        queue = deque([src_id])
        
        while queue:
            current = queue.popleft()
            if current == tgt_id:
                break
            for neighbor in adj[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    parent[neighbor] = current
                    queue.append(neighbor)
        
        if tgt_id not in parent:
            return FindPathResponse(found=False, path=[], path_length=0, entities=[])
        
        # Reconstruct path
        path_ids = []
        node = tgt_id
        while node is not None:
            path_ids.append(node)
            node = parent[node]
        path_ids.reverse()
        
        path_entities = [node_ids[nid] for nid in path_ids if nid in node_ids]
        
        return FindPathResponse(
            found=True,
            path=path_ids,
            path_length=len(path_ids) - 1,
            entities=path_entities
        )
    
    async def get_random_disconnect(self) -> "RandomDisconnectResponse":
        """Get two entities that are not directly linked in the current graph."""
        import random
        
        graph = await self.get_knowledge_graph(label="*", max_nodes=2000)
        nodes = graph.nodes
        edges = graph.edges
        
        if len(nodes) < 2:
            raise LightRAGAPIError("Need at least 2 entities in the knowledge graph")
        
        # Build adjacency set for direct connections
        adj = {n.get('id', ''): set() for n in nodes}
        for edge in edges:
            src = edge.get('source_id') or edge.get('source')
            tgt = edge.get('target_id') or edge.get('target')
            if src in adj and tgt in adj:
                adj[src].add(tgt)
                adj[tgt].add(src)
        
        # Pick two random nodes that are NOT directly connected
        node_list = list(nodes)
        random.shuffle(node_list)
        
        for i, n1 in enumerate(node_list):
            n1_id = n1.get('id', '')
            for n2 in node_list[i + 1:]:
                n2_id = n2.get('id', '')
                if n2_id not in adj.get(n1_id, set()):
                    return RandomDisconnectResponse(entity1=n1, entity2=n2)
        
        raise LightRAGAPIError("All entities are directly connected (complete graph)")
    
    # Graph Exploration and Analysis Methods (9 methods)
    
    async def get_entity_neighbors(self, entity_id: str) -> "EntityNeighborsResponse":
        """Get all direct neighbors of an entity including edge types."""
        graph = await self.get_knowledge_graph(label=entity_id, max_depth=1, max_nodes=2000)
        nodes = {n.get('id', ''): n for n in graph.nodes}
        entity = nodes.get(entity_id)
        if entity is None:
            for n in graph.nodes:
                for key in ('entity_name', 'name', 'label'):
                    if str(n.get(key, '')).lower() == entity_id.lower():
                        entity = n
                        entity_id = n.get('id', entity_id)
                        break
                if entity:
                    break
        if entity is None:
            raise LightRAGAPIError(f"Entity '{entity_id}' not found in the knowledge graph")
        
        neighbor_ids = set()
        neighbor_data = []
        for edge in graph.edges:
            src = edge.get('source_id') or edge.get('source')
            tgt = edge.get('target_id') or edge.get('target')
            if src == entity_id and tgt in nodes and tgt not in neighbor_ids:
                neighbor_ids.add(tgt)
                neighbor_data.append(dict(nodes[tgt], relation=edge.get('type', 'unknown')))
            elif tgt == entity_id and src in nodes and src not in neighbor_ids:
                neighbor_ids.add(src)
                neighbor_data.append(dict(nodes[src], relation=edge.get('type', 'unknown')))
        
        return EntityNeighborsResponse(entity=entity, neighbors=neighbor_data, neighbor_count=len(neighbor_data))
    
    async def get_most_connected_entities(self, top_n: int = 10) -> "MostConnectedResponse":
        """Get top N entities by connection degree."""
        graph = await self.get_knowledge_graph(label="*", max_nodes=3000)
        nodes = {n.get('id', ''): n for n in graph.nodes}
        degree = {nid: 0 for nid in nodes}
        
        for edge in graph.edges:
            src = edge.get('source_id') or edge.get('source')
            tgt = edge.get('target_id') or edge.get('target')
            if src in degree:
                degree[src] += 1
            if tgt in degree:
                degree[tgt] += 1
        
        ranked = sorted(degree.items(), key=lambda x: x[1], reverse=True)[:top_n]
        entities = []
        for nid, deg in ranked:
            node = nodes[nid]
            name = node.get('entity_name') or node.get('name') or node.get('label')
            entities.append(MostConnectedEntity(
                entity_id=nid,
                entity_name=name,
                degree=deg,
                entity=node
            ))
        
        return MostConnectedResponse(entities=entities, graph_is_truncated=graph.is_truncated)
    
    async def get_graph_stats(self) -> "GraphStatsResponse":
        """Get graph statistics: node count, edge count, density, avg degree, etc."""
        graph = await self.get_knowledge_graph(label="*", max_nodes=3000)
        nodes = graph.nodes
        edges = graph.edges
        
        n = len(nodes)
        m = len(edges)
        max_possible_edges = n * (n - 1) / 2 if n > 1 else 1
        density = m / max_possible_edges if max_possible_edges > 0 else 0.0
        avg_degree = (2 * m) / n if n > 0 else 0.0
        
        degree = {node.get('id', ''): 0 for node in nodes}
        for edge in edges:
            src = edge.get('source_id') or edge.get('source')
            tgt = edge.get('target_id') or edge.get('target')
            if src in degree:
                degree[src] += 1
            if tgt in degree:
                degree[tgt] += 1
        
        max_deg = max(degree.values()) if degree else 0
        isolated_count = sum(1 for d in degree.values() if d == 0)
        
        return GraphStatsResponse(
            node_count=n,
            edge_count=m,
            density=round(density, 6),
            avg_degree=round(avg_degree, 2),
            max_degree=max_deg,
            isolated_count=isolated_count,
            is_truncated=graph.is_truncated
        )
    
    async def find_similar_entities(self, entity_id: str, top_n: int = 5) -> "SimilarEntitiesResponse":
        """Find entities similar to the given entity using Jaccard similarity on shared neighbors."""
        graph = await self.get_knowledge_graph(label=entity_id, max_depth=2, max_nodes=3000)
        nodes = {n.get('id', ''): n for n in graph.nodes}
        
        # Build neighbor sets
        neighbors = {nid: set() for nid in nodes}
        for edge in graph.edges:
            src = edge.get('source_id') or edge.get('source')
            tgt = edge.get('target_id') or edge.get('target')
            if src in neighbors and tgt in neighbors:
                neighbors[src].add(tgt)
                neighbors[tgt].add(src)
        
        # Resolve entity
        resolved_id = entity_id
        if resolved_id not in nodes:
            for nid, n in nodes.items():
                for key in ('entity_name', 'name', 'label'):
                    if str(n.get(key, '')).lower() == entity_id.lower():
                        resolved_id = nid
                        break
                if resolved_id != entity_id:
                    break
        
        if resolved_id not in nodes:
            raise LightRAGAPIError(f"Entity '{entity_id}' not found in the knowledge graph")
        
        source_entity = nodes[resolved_id]
        source_neighbors = neighbors.get(resolved_id, set())
        
        similar = []
        for nid in nodes:
            if nid == resolved_id:
                continue
            nbrs = neighbors.get(nid, set())
            intersection = source_neighbors & nbrs
            union = source_neighbors | nbrs
            if not union:
                continue
            jaccard = len(intersection) / len(union)
            if jaccard > 0:
                name = nodes[nid].get('entity_name') or nodes[nid].get('name') or nodes[nid].get('label')
                similar.append(SimilarEntity(
                    entity_id=nid,
                    entity_name=name,
                    similarity=round(jaccard, 4),
                    shared_neighbors=list(intersection),
                    entity=nodes[nid]
                ))
        
        similar.sort(key=lambda x: x.similarity, reverse=True)
        
        return SimilarEntitiesResponse(
            source_entity=source_entity,
            similar_entities=similar[:top_n]
        )
    
    async def get_common_neighbors(self, entity1: str, entity2: str) -> "CommonNeighborsResponse":
        """Get entities connected to both of two given entities."""
        # Fetch subgraph centered on entity1 with enough depth
        graph = await self.get_knowledge_graph(label=entity1, max_depth=5, max_nodes=3000)
        nodes = {n.get('id', ''): n for n in graph.nodes}
        
        def resolve(identifier: str) -> Optional[str]:
            if identifier in nodes:
                return identifier
            for nid, n in nodes.items():
                for key in ('entity_name', 'name', 'label'):
                    if str(n.get(key, '')).lower() == identifier.lower():
                        return nid
            return None
        
        id1 = resolve(entity1)
        id2 = resolve(entity2)
        if id1 is None:
            raise LightRAGAPIError(f"Entity '{entity1}' not found in the knowledge graph")
        if id2 is None:
            # Try fetching from entity2's perspective
            graph2 = await self.get_knowledge_graph(label=entity2, max_depth=5, max_nodes=3000)
            nodes2 = {n.get('id', ''): n for n in graph2.nodes}
            for n in nodes:
                nid = n.get('id', '')
                if nid not in nodes2:
                    nodes2[nid] = n
            nodes = nodes2
            id2 = resolve(entity2)
            if id2 is None:
                raise LightRAGAPIError(f"Entity '{entity2}' not found in the knowledge graph")
        
        e1_data = nodes.get(id1, {})
        e2_data = nodes.get(id2, {})
        
        # Build neighbor sets
        neighbors = {nid: set() for nid in nodes}
        for edge in graph.edges:
            src = edge.get('source_id') or edge.get('source')
            tgt = edge.get('target_id') or edge.get('target')
            if src in neighbors and tgt in neighbors:
                neighbors[src].add(tgt)
                neighbors[tgt].add(src)
        
        common_ids = neighbors.get(id1, set()) & neighbors.get(id2, set())
        common_list = [nodes[nid] for nid in common_ids if nid in nodes]
        
        return CommonNeighborsResponse(
            entity1=e1_data,
            entity2=e2_data,
            common_neighbors=common_list,
            common_count=len(common_list)
        )
    
    async def find_isolated_entities(self) -> "IsolatedEntitiesResponse":
        """Find entities with zero or one connection in the knowledge graph."""
        graph = await self.get_knowledge_graph(label="*", max_nodes=3000)
        nodes = graph.nodes
        degree = {node.get('id', ''): 0 for node in nodes}
        
        for edge in graph.edges:
            src = edge.get('source_id') or edge.get('source')
            tgt = edge.get('target_id') or edge.get('target')
            if src in degree:
                degree[src] += 1
            if tgt in degree:
                degree[tgt] += 1
        
        isolated = [node for node in nodes if degree.get(node.get('id', ''), 0) <= 1]
        
        return IsolatedEntitiesResponse(
            isolated=isolated,
            count=len(isolated),
            graph_is_truncated=graph.is_truncated
        )
    
    async def find_bridge_entities(self) -> "BridgeEntitiesResponse":
        """Find articulation points (bridge entities) whose removal would split the subgraph."""
        graph = await self.get_knowledge_graph(label="*", max_nodes=3000)
        nodes = graph.nodes
        edges = graph.edges
        
        nid_list = [n.get('id', '') for n in nodes]
        node_map = {nid: i for i, nid in enumerate(nid_list)}
        
        # Build adjacency
        adj = [[] for _ in range(len(nid_list))]
        for edge in edges:
            src = edge.get('source_id') or edge.get('source')
            tgt = edge.get('target_id') or edge.get('target')
            if src in node_map and tgt in node_map:
                u, v = node_map[src], node_map[tgt]
                adj[u].append(v)
                adj[v].append(u)
        
        # Tarjan's algorithm for articulation points
        visited = [False] * len(nid_list)
        disc = [0] * len(nid_list)
        low = [0] * len(nid_list)
        parent = [-1] * len(nid_list)
        ap = [False] * len(nid_list)
        time = [0]
        
        def dfs(u: int):
            children = 0
            visited[u] = True
            time[0] += 1
            disc[u] = low[u] = time[0]
            
            for v in adj[u]:
                if not visited[v]:
                    children += 1
                    parent[v] = u
                    dfs(v)
                    low[u] = min(low[u], low[v])
                    if parent[u] == -1 and children > 1:
                        ap[u] = True
                    if parent[u] != -1 and low[v] >= disc[u]:
                        ap[u] = True
                elif v != parent[u]:
                    low[u] = min(low[u], disc[v])
        
        for i in range(len(nid_list)):
            if not visited[i]:
                dfs(i)
        
        bridges = []
        for i, is_ap in enumerate(ap):
            if is_ap:
                nid = nid_list[i]
                name = nodes[i].get('entity_name') or nodes[i].get('name') or nodes[i].get('label')
                bridges.append(BridgeEntity(
                    entity_id=nid,
                    entity_name=name,
                    entity=nodes[i]
                ))
        
        return BridgeEntitiesResponse(
            bridge_entities=bridges,
            count=len(bridges),
            graph_is_truncated=graph.is_truncated
        )
    
    async def get_graph_label_popularity(self) -> "LabelPopularityResponse":
        """Get label popularity from the knowledge graph (wraps /graph/label/popular)."""
        response_data = await self._make_request("GET", "/graph/label/popular")
        return LabelPopularityResponse(**response_data)
    
    async def find_ghost_nodes(self) -> "GhostNodesResponse":
        """Find entities that appear as targets in relations but never as sources (ghost nodes)."""
        graph = await self.get_knowledge_graph(label="*", max_nodes=3000)
        nodes = {n.get('id', ''): n for n in graph.nodes}
        
        source_count = {nid: 0 for nid in nodes}
        target_count = {nid: 0 for nid in nodes}
        
        for edge in graph.edges:
            src = edge.get('source_id') or edge.get('source')
            tgt = edge.get('target_id') or edge.get('target')
            if src in source_count:
                source_count[src] += 1
            if tgt in target_count:
                target_count[tgt] += 1
        
        ghosts = []
        for nid, node in nodes.items():
            if source_count.get(nid, 0) == 0 and target_count.get(nid, 0) > 0:
                name = node.get('entity_name') or node.get('name') or node.get('label')
                ghosts.append(GhostNode(
                    entity_id=nid,
                    entity_name=name,
                    target_count=target_count[nid],
                    source_count=0,
                    entity=node
                ))
        
        ghosts.sort(key=lambda x: x.target_count, reverse=True)
        
        return GhostNodesResponse(
            ghost_nodes=ghosts,
            count=len(ghosts),
            graph_is_truncated=graph.is_truncated
        )
    
    # System Management Methods (4 methods)
    
    async def get_pipeline_status(self) -> PipelineStatusResponse:
        """Get the pipeline status from LightRAG."""
        response_data = await self._make_request("GET", "/documents/pipeline_status")
        return PipelineStatusResponse(**response_data)
    
    async def get_track_status(self, track_id: str) -> TrackStatusResponse:
        """Get the track status for a specific track ID."""
        response_data = await self._make_request("GET", f"/documents/track_status/{track_id}")
        return TrackStatusResponse(**response_data)
    
    async def get_document_status_counts(self) -> StatusCountsResponse:
        """Get document status counts from LightRAG."""
        response_data = await self._make_request("GET", "/documents/status_counts")
        return StatusCountsResponse(**response_data)
    
    async def clear_cache(self, cache_type: Optional[str] = None) -> ClearCacheResponse:
        """Clear LightRAG cache."""
        if cache_type:
            request_data = ClearCacheRequest(cache_type=cache_type).model_dump()
        else:
            request_data = {}
        response_data = await self._make_request("POST", "/documents/clear_cache", request_data)
        return ClearCacheResponse(**response_data)
    
    async def get_health(self) -> HealthResponse:
        """Check LightRAG server health."""
        response_data = await self._make_request("GET", "/health")
        return HealthResponse(**response_data)
