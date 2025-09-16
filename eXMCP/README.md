# MCP Multi-Agent System

**分布式多协议智能体通信与编排框架**

---

## 项目背景与定位

随着大模型（LLM）和多智能体（Multi-Agent）技术的快速发展，越来越多的AI应用场景需要多个智能体协作、分布式部署、异构模型混合、任务自动编排与调度。传统的单协议、单中心、单体式智能体系统难以满足以下需求：

- **多协议异构接入**：不同智能体/模型/工具链可能基于不同的通信协议（如HTTP、WebSocket、gRPC、MCP等）。
- **分布式高可用**：需要支持多中心agent、横向扩展、主备切换、分布式任务队列、自动容错。
- **安全与可观测性**：需要统一认证、细粒度权限、健康监控、自动剔除失联agent、任务全链路追踪。
- **灵活扩展与集成**：支持插件机制、协议适配、第三方系统集成、自动化运维与告警。
- **工程级落地**：易于部署、配置、二次开发，适合团队协作和开源推广。

本项目正是为了解决上述痛点，打造一个**面向未来的分布式多协议多智能体通信与编排平台**。

---

## 技术栈与核心依赖

- **Python 3.8+**：主开发语言，生态丰富，易于扩展。
- **FastAPI**：高性能异步Web框架，支持HTTP/WebSocket服务端。
- **gRPC (grpcio, grpcio-tools)**：高性能RPC通信，支持流式消息、强类型接口。
- **MCP (modelcontextprotocol)**：大模型/智能体生态标准协议，兼容OpenAI、Claude、LangChain、Cursor等。
- **websockets**：WebSocket通信，适合实时、双向、低延迟场景。
- **Redis**：分布式注册表、心跳、任务队列、选主，支持高可用和横向扩展。
- **Uvicorn**：异步ASGI服务器，适合生产环境部署。
- **pydantic**：配置与数据校验，提升健壮性和开发体验。
- **requests/kafka-python/pika/smtplib**：剔除通知推送，支持WebHook、Kafka、RabbitMQ、邮件等。
- **asyncio**：全链路异步/并发，提升吞吐和响应速度。
- **Docker**（推荐）：容器化部署，便于CI/CD和云原生集成。

---

## 架构与核心设计

### 1. 多协议通信层

- **MCP协议**：标准化大模型/智能体生态的消息、任务、上下文、工具调用等，支持流式HTTP、Stdio、WebSocket等多种传输层，兼容主流AI平台。
- **gRPC**：高性能、强类型、支持流式消息，适合高吞吐、低延迟、分布式部署场景。
- **HTTP/REST**：适合与传统Web服务、微服务、前端系统集成，支持RESTful任务分发、结果查询、agent状态监控等。
- **WebSocket**：实时、双向通信，适合需要推送/订阅、低延迟场景。

### 2. 分布式与高可用机制

- **注册/心跳/剔除**：所有agent/中心agent注册、心跳、注销等状态通过Redis同步，中心agent自动剔除失联agent，支持状态查询API。
- **分布式任务队列**：所有任务入队到Redis优先级队列，支持多中心agent/worker并发拉取、分布式调度，天然高可用。
- **自动选主**：中心agent通过Redis SETNX/EXPIRE实现leader选举，主节点负责调度，备节点热备，失联自动切换。
- **剔除通知**：支持WebHook、Kafka、RabbitMQ、邮件、IM等多种推送方式，便于与外部监控/运维系统集成。

### 3. 安全与可观测性

- **API Key认证**：全协议统一API Key认证，支持细粒度权限扩展，安全可控。
- **优先级调度**：任务队列支持优先级，紧急任务优先分发，支持批量任务。
- **自动注册/心跳/剔除**：agent自动注册、定期心跳，中心agent自动剔除失联agent，支持状态查询API。
- **插件机制**：支持自定义插件/中间件，扩展认证、加密、审计、限流等，支持热插拔。

### 4. 插件与扩展机制

- **插件机制**：支持自定义认证、加密、审计、限流等插件，支持热插拔。
- **协议适配**：实现`AgentCommInterface`适配器即可扩展新协议。
- **分布式任务队列/选主**：所有任务入队到Redis，worker/agent从队列出队执行，天然支持分布式和高可用。

---

## 目录结构

```
central_agent/      # 中心智能体（多协议服务端、分布式注册/心跳/剔除/选主/任务队列）
model_agent/        # 大模型智能体（多协议client、自动注册/心跳/注销、API Key自动注入）
mcp_utils/          # 通信协议适配层、分布式注册表、优先级队列、认证、通知、选主等工具
proto/              # gRPC协议定义
examples/           # 多协议端到端演示脚本
```

---

## 协议与通信机制详解

### MCP协议
- **消息格式**：基于JSON-RPC，支持`create_message`、`read_message`、`send_notification`等。
- **流式HTTP**：推荐用`streamablehttp_client/server`，支持大模型生态对接。
- **Stdio/WS**：适合本地子进程、桌面应用、实时场景。
- **兼容性**：可与OpenAI、Claude、LangChain、Cursor等生态无缝集成。

### gRPC
- **proto定义**：支持注册、心跳、任务分发、结果回传、批量任务、优先级等。
- **流式接口**：支持`StreamMessages`、`NextTask`等流式任务分发与结果回传。
- **高性能**：适合大规模分布式部署、低延迟场景。

### HTTP/REST
- **任务分发**：`/task`、`/batch_task`、`/ws_task`等接口，支持单任务、批量任务、优先级。
- **结果查询**：`/task_result/{task_id}`接口，支持任务状态与结果追踪。
- **agent状态监控**：`/agent_status`接口，支持全局健康监控。

### WebSocket
- **实时推送**：支持agent注册、心跳、任务分发、结果回传等全流程实时通信。
- **双向流**：适合需要低延迟、推送/订阅、事件驱动的场景。

---

## 分布式机制与高可用

- **Redis注册表**：所有agent/中心agent注册、心跳、注销等状态通过Redis同步，支持多中心agent横向扩展。
- **分布式优先级队列**：所有任务入队到Redis zset，支持优先级调度、批量任务、分布式worker并发拉取。
- **自动选主**：中心agent通过Redis SETNX/EXPIRE实现leader选举，主节点负责调度，备节点热备，失联自动切换。
- **剔除通知**：支持WebHook、Kafka、RabbitMQ、邮件、IM等多种推送方式，便于与外部监控/运维系统集成。
- **健康监控**：中心agent定期检查agent心跳，超时自动剔除，支持状态查询API。

---

## 快速开始

1. **安装依赖**  
   `pip install -r requirements.txt`
2. **启动Redis服务**  
   推荐本地或云Redis，默认地址`redis://localhost:6379/0`，可通过环境变量配置。
3. **一键启动多协议中心agent和多个model agent**  
   参考`examples/run_demo.py`，支持HTTP/WS/gRPC/MCP多协议混合。
4. **配置API Key、协议、模型类型、通知方式等**  
   可通过`.env`、环境变量或命令行参数灵活配置。

---

## 端到端测试用例

详见`examples/`目录，支持MCP/gRPC/HTTP/WS多协议端到端演示。

- MCP: `test_mcp_agent.py`、`send_mcp_task.py`
- gRPC: `test_grpc_agent.py`、`send_grpc_task.py`
- HTTP: `test_http_agent.py`、`send_http_task.py`
- WebSocket: `test_ws_agent.py`、`send_ws_task.py`

---

## 结果收集/查询API

- 查询任务结果：`GET /task_result/{task_id}`
- 查询所有agent状态：`GET /agent_status`

---

## 高级用法与扩展点

### 分布式多中心agent
- 多实例指向同一Redis即可横向扩展，自动选主、自动剔除失联agent。
- 支持主备切换、分布式任务队列、全局注册表。

### 剔除通知
- 配置WebHook/Kafka/RabbitMQ/邮件/IM等，agent剔除时自动推送告警。
- 可扩展为多种通知方式，便于与外部监控/运维/自动化系统集成。

### 插件机制
- 支持自定义认证、加密、审计、限流等插件，支持热插拔。
- 插件可拦截/扩展注册、心跳、任务、结果等全流程。

### 多协议混合
- 同一agent/中心agent可同时支持多种协议，灵活适配各种业务场景。
- 支持协议动态切换、并发监听、统一任务处理。

### 分布式任务队列/选主
- 所有任务入队到Redis，worker/agent从队列出队执行，天然支持分布式和高可用。
- 选主机制基于Redis，主节点负责调度，备节点热备，失联自动切换。

---

## 适用场景

- 大规模多智能体协作与AI编排
- 分布式自动化与任务调度
- LLM工具链/插件系统/AI平台通信底座
- 科研/教学/竞赛的多agent实验平台


---

## 常见问题

- **如何扩展新协议/插件？**  
  实现`AgentCommInterface`适配器或插件基类，注册到框架即可。
- **如何实现高可用/分布式？**  
  多中心agent/worker指向同一Redis，自动选主、自动剔除、分布式任务队列。
- **如何接入外部监控/通知？**  
  配置WebHook/Kafka/RabbitMQ/邮件/IM等，剔除/异常自动推送。
- **如何与大模型生态对接？**  
  MCP协议兼容OpenAI、Claude、LangChain、Cursor等主流生态，支持流式HTTP、Stdio、WebSocket等多种传输层。
- **如何实现任务优先级和批量任务？**  
  任务结构支持priority字段，中心agent用Redis zset实现优先级队列，支持批量任务分发。
- **如何实现主备切换和高可用？**  
  通过Redis SETNX/EXPIRE实现leader选举，主节点负责调度，备节点热备，失联自动切换。


---

## 实现原理与底层架构细节

本节将系统性地剖析 MCP Multi-Agent System 的核心实现原理、底层架构设计、关键模块的技术细节与工程考量，帮助开发者、架构师、团队成员深入理解系统的可扩展性、健壮性与工程落地能力。

---

### 1. 通信协议适配与统一抽象

#### 1.1 设计动机

在多智能体系统中，**agent**（*智能体，指具备独立决策、任务执行能力的服务进程或容器*）与**中心agent**（*负责注册、调度、任务分发、健康监控的主控节点*）、agent与agent之间的通信协议可能多样（如**HTTP**、**WebSocket**、**gRPC**、**MCP**等）。如果每个业务逻辑都直接依赖具体协议，系统将难以维护和扩展。为此，本项目采用**统一通信抽象层**（*一种面向接口编程的设计模式，将协议细节与业务逻辑解耦*），所有协议都实现同一接口，业务逻辑与协议解耦。

#### 1.2 AgentCommInterface抽象层

**AgentCommInterface**（*智能体通信接口，定义所有协议适配器必须实现的标准方法*）如下：

```python
class AgentCommInterface(abc.ABC):
    @abc.abstractmethod
    async def send_message(self, target: str, content: dict) -> Any: ...
    @abc.abstractmethod
    async def receive_message(self, handler: Callable[[dict], Awaitable[None]]): ...
    @abc.abstractmethod
    async def start(self): ...
```
- **send_message**：发送任务/消息到目标agent或中心。支持异步、流式、批量等多种模式。
- **receive_message**：注册消息处理回调，适配流式（如gRPC/MCP）、推送（如WebSocket）、轮询（如HTTP）等多种消息接收方式。
- **start**：启动协议适配器，建立连接、认证、注册等。

#### 1.3 多协议适配器实现

- **HTTPCommAdapter**：基于**FastAPI**（*现代异步Web框架*）/**requests**/**httpx**，支持RESTful任务分发、结果回传、心跳、注册等。采用**长轮询**（*客户端定期向服务端请求新任务*）或**短轮询**，主动推送结果。
- **WSCommAdapter**：基于**websockets**库（*Python异步WebSocket实现*），支持实时双向通信，自动重连、心跳、任务推送。适合低延迟、事件驱动场景。
- **GRPCCommAdapter**：基于**gRPC**（*Google开源的高性能远程过程调用框架，支持多语言、流式通信、强类型接口*），支持流式任务分发、结果回传、注册/心跳等。**proto**（*gRPC的IDL接口描述语言*）定义支持多种消息类型，适合高吞吐、分布式部署。
- **MCPCommAdapter**：基于官方**mcp**库（*Model Context Protocol，AI/LLM生态的开放通信协议*），支持流式HTTP、Stdio、WebSocket等多种传输层，兼容大模型生态（如OpenAI、Claude、LangChain、Cursor等）。

**工程考量**：
- 适配器自动注入**API Key**（*访问令牌，用于认证和权限控制*）、自动注册/心跳/注销，所有协议可并发监听、动态切换。
- 支持**协议降级**（*主协议不可用时自动切换到备选协议*）、**自动重连**、**故障转移**，提升系统鲁棒性。
- 业务层只需依赖AgentCommInterface，协议切换零侵入。

---

### 2. 分布式注册、心跳与剔除机制

#### 2.1 分布式注册表

**分布式注册表**（*Distributed Registry*）是指所有agent和中心agent的注册、心跳、注销等状态通过**Redis**（*高性能分布式内存数据库，支持多种数据结构*）的hash结构同步。每个agent注册时写入`agents`和`agent_heartbeat`，中心agent定期扫描心跳时间，超时自动剔除。

**实现方式**：
- 采用Redis的**hash**（*哈希表，键值对集合*）结构存储agent注册信息和心跳时间。
- agent注册时写入`agents`和`agent_heartbeat`，注销时删除。
- 所有中心agent/worker共享同一Redis，实现横向扩展和高可用。

**关键代码**：
```python
def register_agent(self, agent_id, meta):
    self.r.hset('agents', agent_id, json.dumps(meta))
    self.r.hset('agent_heartbeat', agent_id, time.time())
def heartbeat(self, agent_id):
    self.r.hset('agent_heartbeat', agent_id, time.time())
def unregister_agent(self, agent_id):
    self.r.hdel('agents', agent_id)
    self.r.hdel('agent_heartbeat', agent_id)
```

#### 2.2 健康监控与自动剔除

**健康监控**（*Health Monitoring*）是指中心agent通过后台线程定期检查所有agent的心跳时间，超时未心跳的agent会被自动剔除（包括注册表、状态、任务队列等），并通过**WebHook**（*HTTP回调*）/**Kafka**（*分布式消息队列*）/**RabbitMQ**（*消息中间件*）/**邮件**/**IM**等方式推送剔除通知。

**工程考量**：
- 剔除机制支持多种通知方式，便于与外部监控/运维系统集成。
- 支持状态查询API，便于健康监控和可视化。

---

### 3. 分布式任务队列与优先级调度

#### 3.1 Redis优先级队列

**分布式任务队列**（*Distributed Task Queue*）采用Redis的**zset**（*有序集合*）实现。任务结构支持`priority`字段，中心agent/worker可并发拉取优先级最高的任务，天然支持分布式和高可用。

**优先级调度**（*Priority Scheduling*）是指任务根据`priority`字段自动排序，紧急任务优先分发，支持批量任务、任务重试、超时、取消等。

**工程考量**：
- 支持任务重试、超时、取消、批量任务等高级调度策略。
- 任务状态、结果、日志可通过API/监控平台实时观测。

---

### 4. 自动选主与高可用

#### 4.1 Redis选主机制

**自动选主**（*Leader Election*）是指中心agent通过Redis的SETNX/EXPIRE实现leader选举。所有中心agent竞争同一个key（如`leader`），抢到的为主节点，定期刷新key，失联自动切换。

**主备切换**（*Failover*）与**分布式调度**（*Distributed Scheduling*）保证系统高可用，支持多活、主备、分区容错等多种高可用部署模式。

---

### 5. 插件机制与可扩展性

#### 5.1 插件接口与热插拔

**插件机制**（*Plugin System*）支持自定义插件/中间件，开发者可实现认证、加密、审计、限流、日志、监控等插件，按需注册到agent或中心agent。插件可在注册、心跳、任务分发、结果回传、剔除等事件点拦截和扩展逻辑，支持热插拔、配置化启用/禁用。

**工程考量**：
- 插件机制支持团队协作、敏捷开发、灰度发布、动态扩展。
- 插件可与主流监控、认证、加密、运维平台集成。

---

### 6. 安全、可观测性与运维

#### 6.1 API Key认证与权限管理

**API Key认证**（*API Key Authentication*）是指所有协议适配器自动注入API Key，中心agent统一校验，支持细粒度权限扩展。支持动态Key管理、权限分级、敏感操作审计。

#### 6.2 日志与监控

**日志与监控**（*Logging & Monitoring*）支持全链路日志输出，接入ELK、Prometheus、Grafana等监控系统。agent/任务/中心agent状态可通过API/通知/监控平台实时观测。

#### 6.3 自动化运维与告警

**自动化运维与告警**（*Ops & Alerting*）支持剔除通知通过WebHook、Kafka、RabbitMQ、邮件、IM等多种方式推送，便于自动化运维和告警。支持与企业微信、钉钉、飞书、PagerDuty等平台集成。

---

### 7. 端到端任务流转与多协议混合

#### 7.1 端到端流程

1. 用户/上游通过任意协议提交任务，中心agent入队。
2. agent通过协议适配器拉取任务，处理后回传结果。
3. 任务状态、结果、agent健康等全链路可观测。
4. 支持多协议混合、分布式高可用、主备切换、自动剔除、通知推送。

#### 7.2 多协议混合与动态切换

**多协议混合**（*Multi-Protocol Hybrid*）是指同一agent/中心agent可同时支持多种协议，协议适配器可动态切换、并发监听。支持协议降级、自动重连、故障转移，提升系统鲁棒性。

---

### 8. 工程落地与最佳实践

#### 8.1 容器化与云原生

**容器化**（*Containerization*）推荐用Docker容器化部署，支持Kubernetes、云原生平台。Redis可用云服务或高可用集群，支持多数据中心。

#### 8.2 CI/CD与自动化测试

**CI/CD**（*持续集成/持续部署*）推荐集成GitHub Actions、GitLab CI等自动化测试与部署。提供端到端测试用例，覆盖多协议、分布式、插件、通知等全链路。

#### 8.3 配置与环境管理

**配置与环境管理**（*Configuration & Environment Management*）所有参数支持env/配置文件/命令行切换，便于多环境部署和动态扩展。支持多租户、分组、权限分级等高级配置。

---

### 9. 典型应用场景与扩展方向

- **AI多智能体协作平台**：支持多模型、多协议、多任务协作，适合AI平台、RAG、自动化链路。
- **分布式自动化与调度**：适合大规模分布式任务调度、自动化运维、云原生微服务编排。
- **LLM工具链/插件系统**：作为AI工具链、插件系统的通信底座，支持即插即用和生态扩展。
- **科研/教学/竞赛平台**：支持多agent实验、竞赛、教学演示，便于快速搭建和扩展。

---

### 10. 未来规划与社区协作

- 支持更多协议（如MQTT、SSE、ZeroMQ等）、更多云原生特性（如服务网格、服务发现）。
- 丰富插件生态，支持更多认证、加密、监控、审计、运维插件。
- 推动与主流AI平台、工具链、云服务的深度集成。
- 欢迎社区贡献协议适配、插件开发、分布式调度、自动化运维等各类PR和Issue。

---

**术语解释索引**  
- **Agent**：具备独立决策、任务执行能力的服务进程或容器。
- **中心agent**：负责注册、调度、任务分发、健康监控的主控节点。
- **MCP协议**：Model Context Protocol，AI/LLM生态的开放通信协议，支持流式HTTP、Stdio、WebSocket等多种传输层。
- **gRPC**：Google开源的高性能远程过程调用框架，支持多语言、流式通信、强类型接口。
- **WebSocket**：一种在单个TCP连接上进行全双工通信的协议，适合实时、低延迟场景。
- **HTTP/REST**：超文本传输协议/表述性状态转移，Web服务的主流通信协议。
- **Redis**：高性能分布式内存数据库，支持多种数据结构，常用于缓存、消息队列、分布式锁等。
- **API Key**：访问令牌，用于认证和权限控制。
- **优先级队列**：一种数据结构，支持元素按优先级自动排序，常用于任务调度。
- **主备切换/选主**：分布式系统中通过选举机制确定主节点，主节点失联时自动切换到备节点。
- **插件机制**：支持自定义扩展点，便于认证、加密、审计、限流、日志、监控等功能的灵活插拔。
- **WebHook**：HTTP回调机制，常用于事件通知和自动化集成。
- **Kafka/RabbitMQ**：主流分布式消息队列/中间件，支持高吞吐、可靠消息传递。
- **CI/CD**：持续集成/持续部署，自动化测试与发布的工程体系。
- **云原生**：以容器、微服务、自动化运维为核心的现代分布式系统设计理念。

