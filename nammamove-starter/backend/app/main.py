from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from .engine import EDGES, Incident, route, service_state

app = FastAPI(title='NammaMove API', version='0.1.0', description='Simulation-only disruption-aware mobility API')

class RouteRequest(BaseModel):
    origin: str = Field(min_length=1)
    destination: str = Field(min_length=1)
    incidents: list['IncidentRequest'] = Field(default_factory=list)

class IncidentRequest(BaseModel):
    id: str
    affected_edges: list[str]
    kind: str = 'disruption'
    verified: bool = False
    delay_minutes: int = Field(default=0, ge=0, le=1440)
    blocked: bool = False

@app.get('/health')
def health():
    return {'status':'ok', 'mode':'simulation'}

@app.get('/network')
def network():
    return {'stops':sorted(set([x.source for x in EDGES]+[x.target for x in EDGES])), 'edges':[e.__dict__ for e in EDGES], 'mode':'simulation'}

@app.post('/journeys/plan')
def plan(req: RouteRequest):
    incidents = [Incident(i.id, tuple(i.affected_edges), i.kind, i.verified, i.delay_minutes, i.blocked) for i in req.incidents]
    result = route(req.origin, req.destination, incidents)
    if result is None:
        raise HTTPException(status_code=404, detail='No route found in the sample network')
    return result

@app.get('/services/status')
def status(last_seen_seconds: int | None = None, operator_cancelled: bool = False):
    service, feed = service_state(last_seen_seconds, operator_cancelled)
    return {'serviceStatus':service,'feedStatus':feed,'notice':'Missing GPS data alone never confirms cancellation.'}
