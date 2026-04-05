from app import db
from app.models.api_endpoint import APIEndpoint


class APIEndpointService:
    @staticmethod
    def get_all_for_project(project_id):
        return (
            APIEndpoint.query.filter_by(project_id=project_id)
            .order_by(APIEndpoint.updated_at.desc())
            .all()
        )

    @staticmethod
    def get(id):
        return db.session.get(APIEndpoint, id)

    @staticmethod
    def create(project_id, path, method, description="", parameters=None,
               request_schema=None, response_schema=None, status_codes=None):
        endpoint = APIEndpoint(
            project_id=project_id,
            path=path,
            method=method,
            description=description,
            request_schema=request_schema or {},
            response_schema=response_schema or {},
        )
        db.session.add(endpoint)
        db.session.commit()
        return endpoint

    @staticmethod
    def update(endpoint, path=None, method=None, description=None,
               request_schema=None, response_schema=None):
        if path is not None:
            endpoint.path = path
        if method is not None:
            endpoint.method = method
        if description is not None:
            endpoint.description = description
        if request_schema is not None:
            endpoint.request_schema = request_schema
        if response_schema is not None:
            endpoint.response_schema = response_schema
        db.session.commit()
        return endpoint

    @staticmethod
    def delete(endpoint):
        db.session.delete(endpoint)
        db.session.commit()
