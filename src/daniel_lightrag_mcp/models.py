"""
Pydantic models for LightRAG API requests and responses.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


# Enums for status types and mode parameters
class DocStatus(str, Enum):
    """Document status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    DELETED = "deleted"


class QueryMode(str, Enum):
    """Query mode enumeration."""
    NAIVE = "naive"
    LOCAL = "local"
    GLOBAL = "global"
    HYBRID = "hybrid"


class PipelineStatus(str, Enum):
    """Pipeline status enumeration."""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# Common Models
class TextDocument(BaseModel):
    """Text document model."""
    title: Optional[str] = None
    content: str = Field(..., description="Document content")
    metadata: Optional[Dict[str, Any]] = None


class PaginationInfo(BaseModel):
    """Pagination information model."""
    page: int = Field(..., description="Page number")
    page_size: int = Field(..., description="Number of items per page")
    total_count: int = Field(..., description="Total number of items")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")


class ValidationError(BaseModel):
    """Validation error model."""
    loc: List[Union[str, int]]
    msg: str
    type: str


class HTTPValidationError(BaseModel):
    """HTTP validation error model."""
    detail: List[ValidationError]


# Document Management Request Models
class InsertTextRequest(BaseModel):
    """Request model for inserting a single text document."""
    text: str = Field(..., description="Text content to insert")
    file_source: str = Field(default="text_input.txt", description="Source file name for the text")


class InsertTextsRequest(BaseModel):
    """Request model for inserting multiple text documents."""
    texts: List[str] = Field(..., description="List of text strings to insert")
    file_sources: List[str] = Field(default_factory=list, description="List of file sources for the texts")


class DeleteDocRequest(BaseModel):
    """Request model for deleting a document by ID."""
    doc_ids: List[str] = Field(..., description="List of document IDs to delete")


class DeleteEntityRequest(BaseModel):
    """Request model for deleting an entity."""
    entity_id: str = Field(..., description="ID of the entity to delete")
    entity_name: str = Field(..., description="Name of the entity to delete")


class DeleteRelationRequest(BaseModel):
    """Request model for deleting a relation."""
    relation_id: str = Field(..., description="ID of the relation to delete")
    source_entity: str = Field(..., description="Source entity name")
    target_entity: str = Field(..., description="Target entity name")


class DocumentsRequest(BaseModel):
    """Request model for paginated documents."""
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(10, ge=1, le=100, description="Number of items per page")
    status_filter: Optional[DocStatus] = None


class ClearCacheRequest(BaseModel):
    """Request model for clearing cache."""
    cache_type: Optional[str] = None


# Query Request Models
class QueryRequest(BaseModel):
    """Request model for text queries."""
    query: str = Field(..., description="Query text")
    mode: QueryMode = Field(QueryMode.HYBRID, description="Query mode")
    only_need_context: bool = Field(False, description="Whether to only return context")
    stream: bool = Field(False, description="Whether to stream results")


# Knowledge Graph Request Models
class EntityUpdateRequest(BaseModel):
    """Request model for updating an entity."""
    entity_id: str = Field(..., description="ID of the entity to update")
    entity_name: str = Field(..., description="Name of the entity to update")
    updated_data: Dict[str, Any] = Field(..., description="Updated data for the entity")


class RelationUpdateRequest(BaseModel):
    """Request model for updating a relation."""
    # relation_id: str = Field(..., description="ID of the relation to update")
    source_id: str = Field(..., description="Source entity ID")
    target_id: str = Field(..., description="Target entity ID")
    updated_data: Dict[str, Any] = Field(..., description="Updated data for the relation")


class EntityExistsRequest(BaseModel):
    """Request model for checking if entity exists."""
    entity_name: str = Field(..., description="Name of the entity to check")


# Authentication Request Models
class LoginRequest(BaseModel):
    """Request model for login."""
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")


# Document Management Response Models
class InsertResponse(BaseModel):
    """Response model for document insertion."""
    status: str = Field(..., description="Insertion status")
    message: str = Field(..., description="Status message")
    track_id: str = Field(..., description="Tracking ID for the insertion")
    id: Optional[str] = None


class ScanResponse(BaseModel):
    """Response model for document scanning."""
    status: str = Field(..., description="Scanning status")
    message: str = Field(..., description="Status message")
    track_id: str = Field(..., description="Tracking ID for the scan operation")
    new_documents: List[str] = Field(default_factory=list, description="List of new document names")
    message: Optional[str] = None


class UploadResponse(BaseModel):
    """Response model for file upload."""
    status: str = Field(..., description="Upload status")
    message: Optional[str] = None
    track_id: Optional[str] = Field(None, description="Track ID for upload")


class DocumentInfo(BaseModel):
    """Document information model."""
    id: str = Field(..., description="Document ID")
    title: Optional[str] = None
    status: DocStatus = Field(..., description="Document status")
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class DocumentsResponse(BaseModel):
    """Response model for retrieving documents."""
    statuses: Dict[str, Any] = Field(default_factory=dict, description="Document statuses")


class PaginatedDocsResponse(BaseModel):
    """Response model for paginated documents."""
    documents: List[DocumentInfo] = Field(default_factory=list)
    pagination: PaginationInfo = Field(..., description="Pagination information")
    status_counts: Dict[str, int] = Field(default_factory=dict, description="Status counts")


class DeleteDocByIdResponse(BaseModel):
    """Response model for document deletion by ID."""
    status: str = Field(..., description="Deletion status")
    message: Optional[str] = None
    doc_id: Optional[str] = Field(None, description="ID of the deleted document")


class ClearDocumentsResponse(BaseModel):
    """Response model for clearing all documents."""
    status: str = Field(..., description="Clearing status")
    message: Optional[str] = None


class PipelineStatusResponse(BaseModel):
    """Response model for pipeline status."""
    autoscanned: bool = Field(..., description="Whether auto-scanning is enabled")
    busy: bool = Field(..., description="Whether pipeline is busy")
    job_name: Optional[str] = None
    job_start: Optional[str] = None
    docs: Optional[int] = None
    batchs: Optional[int] = None
    cur_batch: Optional[int] = None
    request_pending: Optional[bool] = None
    latest_message: Optional[str] = None
    history_messages: Optional[List[str]] = None
    update_status: Optional[Dict[str, Any]] = None
    progress: Optional[float] = Field(None, ge=0, le=100, description="Progress percentage")
    current_task: Optional[str] = None
    message: Optional[str] = None


class TrackStatusResponse(BaseModel):
    """Response model for track status."""
    track_id: str = Field(..., description="Track ID")
    documents: List[Dict[str, Any]] = Field(default_factory=list, description="Documents in track")
    total_count: int = Field(0, description="Total document count")
    status_summary: Dict[str, Any] = Field(default_factory=dict, description="Status summary")


class StatusCountsResponse(BaseModel):
    """Response model for document status counts."""
    status_counts: Dict[str, int] = Field(..., description="Status counts mapping")


class ClearCacheResponse(BaseModel):
    """Response model for cache clearing."""
    status: str = Field(..., description="Cache clearing status")
    message: str = Field(..., description="Status message")
    cache_type: Optional[str] = None
    message: Optional[str] = None


class DeletionResult(BaseModel):
    """Response model for entity/relation deletion."""
    deleted: bool = Field(..., description="Whether deletion was successful")
    id: str = Field(..., description="ID of the deleted item")
    type: str = Field(..., description="Type of deleted item (entity/relation)")
    message: Optional[str] = None


# Query Response Models
class QueryResult(BaseModel):
    """Query result model."""
    document_id: str = Field(..., description="Document ID")
    snippet: str = Field(..., description="Text snippet")
    score: Optional[float] = Field(None, ge=0, le=1)
    metadata: Optional[Dict[str, Any]] = None


class QueryResponse(BaseModel):
    """Response model for text queries."""
    response: str = Field(..., description="Query response text")
    query: Optional[str] = None
    results: Optional[List[QueryResult]] = None
    total_results: Optional[int] = None
    processing_time: Optional[float] = None
    context: Optional[str] = None


# Knowledge Graph Response Models
class EntityInfo(BaseModel):
    """Entity information model."""
    id: str = Field(..., description="Entity ID")
    name: str = Field(..., description="Entity name")
    type: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class RelationInfo(BaseModel):
    """Relation information model."""
    id: str = Field(..., description="Relation ID")
    source_entity: str = Field(..., description="Source entity ID")
    target_entity: str = Field(..., description="Target entity ID")
    type: str = Field(..., description="Relation type")
    properties: Dict[str, Any] = Field(default_factory=dict)
    weight: Optional[float] = Field(None, ge=0, le=1)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class GraphResponse(BaseModel):
    """Response model for knowledge graph."""
    nodes: List[Dict[str, Any]] = Field(default_factory=list, description="Graph nodes (entities)")
    edges: List[Dict[str, Any]] = Field(default_factory=list, description="Graph edges (relations)")
    is_truncated: bool = Field(False, description="Whether the graph is truncated")
    
    @property
    def entities(self) -> List[Dict[str, Any]]:
        """Alias for nodes to maintain backward compatibility."""
        return self.nodes
    
    @property
    def relations(self) -> List[Dict[str, Any]]:
        """Alias for edges to maintain backward compatibility."""
        return self.edges


class LabelsResponse(BaseModel):
    """Response model for graph labels."""
    labels: List[str] = Field(default_factory=list, description="List of graph labels")


class EntityExistsResponse(BaseModel):
    """Response model for entity existence check."""
    exists: bool = Field(..., description="Whether entity exists")
    entity_name: Optional[str] = None
    entity_id: Optional[str] = None


class EntityUpdateResponse(BaseModel):
    """Response model for entity update."""
    status: str = Field(..., description="Update status")
    message: str = Field(..., description="Update message")
    data: Dict[str, Any] = Field(..., description="Updated entity data")


class RelationUpdateResponse(BaseModel):
    """Response model for relation update."""
    status: str = Field(..., description="Update status")
    message: str = Field(..., description="Update message")
    data: Dict[str, Any] = Field(..., description="Updated relation data")


# System Management Response Models
class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str = Field(..., description="Health status")
    version: Optional[str] = None
    uptime: Optional[float] = None
    database_status: Optional[str] = None
    cache_status: Optional[str] = None
    message: Optional[str] = None


# Authentication Response Models
class AuthStatusResponse(BaseModel):
    """Response model for authentication status."""
    authenticated: bool = Field(..., description="Whether user is authenticated")
    user: Optional[str] = None


class LoginResponse(BaseModel):
    """Response model for login."""
    success: bool = Field(..., description="Whether login was successful")
    token: Optional[str] = None
    user: Optional[str] = None
    message: Optional[str] = None


# Ollama API Models (for completeness)
class OllamaVersionResponse(BaseModel):
    """Response model for Ollama version."""
    version: str = Field(..., description="Ollama version")


class OllamaTagsResponse(BaseModel):
    """Response model for Ollama tags."""
    models: List[Dict[str, Any]] = Field(default_factory=list)


class OllamaProcessResponse(BaseModel):
    """Response model for Ollama running processes."""
    models: List[Dict[str, Any]] = Field(default_factory=list)


class OllamaGenerateRequest(BaseModel):
    """Request model for Ollama generate."""
    model: str = Field(..., description="Model name")
    prompt: str = Field(..., description="Prompt text")
    stream: bool = Field(False, description="Whether to stream response")


class OllamaChatMessage(BaseModel):
    """Chat message model for Ollama."""
    role: str = Field(..., description="Message role (user/assistant)")
    content: str = Field(..., description="Message content")


class OllamaChatRequest(BaseModel):
    """Request model for Ollama chat."""
    model: str = Field(..., description="Model name")
    messages: List[OllamaChatMessage] = Field(..., description="Chat messages")
    stream: bool = Field(False, description="Whether to stream response")


# File upload models
class Body_upload_to_input_dir_documents_upload_post(BaseModel):
    """Request body for file upload."""
    file: bytes = Field(..., description="File content")


class Body_login_login_post(BaseModel):
    """Request body for login."""
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")


# Status response models
class DocStatusResponse(BaseModel):
    """Response model for document status."""
    document_id: str = Field(..., description="Document ID")
    status: DocStatus = Field(..., description="Document status")
    message: Optional[str] = None


class DocsStatusesResponse(BaseModel):
    """Response model for multiple document statuses."""
    statuses: List[DocStatusResponse] = Field(default_factory=list)
    total: int = Field(0, ge=0)


# Knowledge Graph traversal models

class FindPathRequest(BaseModel):
    """Request model for finding a path between two entities."""
    source_entity: str = Field(..., description="Source entity name or ID")
    target_entity: str = Field(..., description="Target entity name or ID")


class FindPathResponse(BaseModel):
    """Response model for entity path finding."""
    found: bool = Field(..., description="Whether a path was found")
    path: List[str] = Field(default_factory=list, description="Entity IDs along the path")
    path_length: int = Field(0, description="Number of hops in the path")
    entities: List[Dict[str, Any]] = Field(default_factory=list, description="Entity details along the path")


class RandomEntityResponse(BaseModel):
    """Response model for a random entity."""
    entity: Dict[str, Any] = Field(..., description="Random entity data")


class RandomDisconnectResponse(BaseModel):
    """Response model for two random disconnected entities."""
    entity1: Dict[str, Any] = Field(..., description="First entity")
    entity2: Dict[str, Any] = Field(..., description="Second entity")


# Graph exploration and analysis models

class EntityNeighborsResponse(BaseModel):
    """Response model for entity neighbors."""
    entity: Dict[str, Any] = Field(..., description="The query entity")
    neighbors: List[Dict[str, Any]] = Field(default_factory=list, description="Direct neighbor entities")
    neighbor_count: int = Field(0, description="Number of direct neighbors")


class MostConnectedEntity(BaseModel):
    """A ranked entity by connection degree."""
    entity_id: str = Field(..., description="Entity ID")
    entity_name: Optional[str] = None
    degree: int = Field(..., description="Number of connections (degree)")
    entity: Dict[str, Any] = Field(default_factory=dict, description="Full entity data")


class MostConnectedResponse(BaseModel):
    """Response model for most connected entities."""
    entities: List[MostConnectedEntity] = Field(default_factory=list, description="Ranked entities")
    graph_is_truncated: bool = Field(False, description="Whether the subgraph was truncated")


class GraphStatsResponse(BaseModel):
    """Response model for graph statistics."""
    node_count: int = Field(0, description="Total nodes in the subgraph")
    edge_count: int = Field(0, description="Total edges in the subgraph")
    density: float = Field(0.0, description="Graph density (0-1)")
    avg_degree: float = Field(0.0, description="Average degree")
    max_degree: int = Field(0, description="Maximum degree of any node")
    isolated_count: int = Field(0, description="Nodes with zero connections")
    is_truncated: bool = Field(False, description="Whether the subgraph was truncated")


class SimilarEntity(BaseModel):
    """An entity similar to the query entity."""
    entity_id: str = Field(..., description="Entity ID")
    entity_name: Optional[str] = None
    similarity: float = Field(..., ge=0, le=1, description="Jaccard similarity score")
    shared_neighbors: List[str] = Field(default_factory=list, description="Shared neighbor IDs")
    entity: Dict[str, Any] = Field(default_factory=dict, description="Full entity data")


class SimilarEntitiesResponse(BaseModel):
    """Response model for similar entities."""
    source_entity: Dict[str, Any] = Field(..., description="The query entity")
    similar_entities: List[SimilarEntity] = Field(default_factory=list, description="Similar entities ranked by similarity")


class CommonNeighborsResponse(BaseModel):
    """Response model for common neighbors between two entities."""
    entity1: Dict[str, Any] = Field(..., description="First entity")
    entity2: Dict[str, Any] = Field(..., description="Second entity")
    common_neighbors: List[Dict[str, Any]] = Field(default_factory=list, description="Common neighbor entities")
    common_count: int = Field(0, description="Number of common neighbors")


class IsolatedEntitiesResponse(BaseModel):
    """Response model for isolated entities."""
    isolated: List[Dict[str, Any]] = Field(default_factory=list, description="Isolated entities")
    count: int = Field(0, description="Number of isolated entities found")
    graph_is_truncated: bool = Field(False, description="Whether the subgraph was truncated")


class BridgeEntity(BaseModel):
    """An articulation point entity."""
    entity_id: str = Field(..., description="Entity ID")
    entity_name: Optional[str] = None
    entity: Dict[str, Any] = Field(default_factory=dict, description="Full entity data")


class BridgeEntitiesResponse(BaseModel):
    """Response model for bridge entities (articulation points)."""
    bridge_entities: List[BridgeEntity] = Field(default_factory=list, description="Bridge/articulation point entities")
    count: int = Field(0, description="Number of bridge entities found")
    graph_is_truncated: bool = Field(False, description="Whether the subgraph was truncated")


class LabelPopularityResponse(BaseModel):
    """Response model for label popularity."""
    labels: List[str] = Field(default_factory=list, description="Popular labels sorted by degree (highest first)")


class GhostNode(BaseModel):
    """A ghost node: frequently targeted but never a source."""
    entity_id: str = Field(..., description="Entity ID")
    entity_name: Optional[str] = None
    target_count: int = Field(0, description="Times this entity appears as a target")
    source_count: int = Field(0, description="Times this entity appears as a source")
    entity: Dict[str, Any] = Field(default_factory=dict, description="Full entity data")


class GhostNodesResponse(BaseModel):
    """Response model for ghost node analysis."""
    ghost_nodes: List[GhostNode] = Field(default_factory=list, description="Ghost node entities (target-only)")
    count: int = Field(0, description="Number of ghost nodes found")
    graph_is_truncated: bool = Field(False, description="Whether the subgraph was truncated")