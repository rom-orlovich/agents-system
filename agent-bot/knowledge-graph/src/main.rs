use actix_cors::Cors;
use actix_web::{web, App, HttpResponse, HttpServer, Responder};
use serde::{Deserialize, Serialize};
use std::sync::Mutex;

#[derive(Debug, Clone, Serialize, Deserialize)]
struct Entity {
    id: String,
    entity_type: String,
    name: String,
    metadata: serde_json::Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct Relationship {
    from_id: String,
    to_id: String,
    relationship_type: String,
}

struct AppState {
    entities: Mutex<Vec<Entity>>,
    relationships: Mutex<Vec<Relationship>>,
}

async fn health() -> impl Responder {
    HttpResponse::Ok().json(serde_json::json!({
        "status": "healthy",
        "service": "knowledge-graph"
    }))
}

async fn create_entity(
    entity: web::Json<Entity>,
    data: web::Data<AppState>,
) -> impl Responder {
    let mut entities = data.entities.lock().unwrap();
    entities.push(entity.into_inner());
    HttpResponse::Created().json(serde_json::json!({"status": "created"}))
}

async fn list_entities(data: web::Data<AppState>) -> impl Responder {
    let entities = data.entities.lock().unwrap();
    HttpResponse::Ok().json(&*entities)
}

async fn create_relationship(
    relationship: web::Json<Relationship>,
    data: web::Data<AppState>,
) -> impl Responder {
    let mut relationships = data.relationships.lock().unwrap();
    relationships.push(relationship.into_inner());
    HttpResponse::Created().json(serde_json::json!({"status": "created"}))
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init();

    let app_state = web::Data::new(AppState {
        entities: Mutex::new(Vec::new()),
        relationships: Mutex::new(Vec::new()),
    });

    HttpServer::new(move || {
        let cors = Cors::permissive();

        App::new()
            .wrap(cors)
            .app_data(app_state.clone())
            .route("/health", web::get().to(health))
            .route("/api/entities", web::post().to(create_entity))
            .route("/api/entities", web::get().to(list_entities))
            .route("/api/relationships", web::post().to(create_relationship))
    })
    .bind(("0.0.0.0", 4000))?
    .run()
    .await
}
