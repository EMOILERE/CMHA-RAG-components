import argparse
from mcp_utils.registry import AgentRegistry
import multiprocessing
import uvicorn
import os

def start_http_server(host, port):
    uvicorn.run("central_agent.http_server:app", host=host, port=port, reload=False)

def start_ws_server(host, port):
    uvicorn.run("central_agent.ws_server:app", host=host, port=port, reload=False)

def start_grpc_server(host, port):
    import grpc
    from concurrent import futures
    import proto.agent_comm_pb2 as pb2
    import proto.agent_comm_pb2_grpc as pb2_grpc
    from central_agent.grpc_server import AgentCommServicer
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    pb2_grpc.add_AgentCommServicer_to_server(AgentCommServicer(), server)
    server.add_insecure_port(f'{host}:{port}')
    print(f"[CentralAgent] gRPC server running at {host}:{port}")
    server.start()
    server.wait_for_termination()

def main():
    parser = argparse.ArgumentParser(description='Central Agent for MCP Multi-Agent System')
    parser.add_argument('--protocols', nargs='+', default=['http'], help='Communication protocols, e.g. http ws grpc')
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--http-port', type=int, default=8000)
    parser.add_argument('--ws-port', type=int, default=8001)
    parser.add_argument('--grpc-port', type=int, default=50051)
    args = parser.parse_args()

    registry = AgentRegistry()
    print(f"[CentralAgent] Starting with protocols: {args.protocols}")
    procs = []
    if 'http' in args.protocols:
        p = multiprocessing.Process(target=start_http_server, args=(args.host, args.http_port))
        p.start()
        procs.append(p)
    if 'ws' in args.protocols:
        p = multiprocessing.Process(target=start_ws_server, args=(args.host, args.ws_port))
        p.start()
        procs.append(p)
    if 'grpc' in args.protocols:
        p = multiprocessing.Process(target=start_grpc_server, args=(args.host, args.grpc_port))
        p.start()
        procs.append(p)
    for p in procs:
        p.join()

if __name__ == '__main__':
    main() 