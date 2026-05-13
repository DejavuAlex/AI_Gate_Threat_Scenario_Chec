# 研究与技术决策

**功能**：院区数据同步配置管理  
**分支**：sml-8241  
**创建时间**：2026年2月5日

## 技术上下文

### 依赖的系统组件

#### push_record 表（由其他需求定义）
```sql
CREATE TABLE push_record (
    id BIGSERIAL PRIMARY KEY,
    config_id BIGINT NOT NULL COMMENT '推送配置ID(关联data_push_configuration表)',
    data_id BIGINT NOT NULL COMMENT '业务数据ID(关联qc_data表)',
    push_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '推送时间',
    status VARCHAR(20) NOT NULL COMMENT '推送状态: SUCCESS(成功) / FAILED(失败)',
    failure_reason TEXT COMMENT '失败原因(仅在status=FAILED时有值)',
    retry_count INT NOT NULL DEFAULT 0 COMMENT '当前重试次数(0-288)',
    next_retry_time TIMESTAMP COMMENT '下次重试时间(仅在status=FAILED且retry_count<288时有值)',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

**关键约束**：
- `config_id` 关联本需求的配置表 ID
- 最近推送时间 = 查询 `push_time` 字段
- 推送状态逻辑：
  - 配置停用时 → "已停用"
  - `status='SUCCESS'` → "实时推送中"
  - `status='FAILED'` → "推送异常（重试中）"

### 技术栈决策

#### Backend Framework
**Decision**: Spring Boot 3.x + MyBatis  
**Rationale**:
- 符合宪章要求的技术栈（章程 Technology Stack Constraints）
- 已有项目使用相同技术栈，保持一致性
- MyBatis 提供灵活的 SQL 映射，适合复杂查询（如关联 push_record 表）

**Alternatives considered**:
- JPA/Hibernate：更适合简单 CRUD，但复杂关联查询不如 MyBatis 灵活

#### 数据库设计
**Decision**: PostgreSQL with Flyway Migration  
**Rationale**:
- 符合宪章数据完整性要求（章程 IV. Data Integrity）
- Flyway 版本化管理 schema 变更
- PostgreSQL 支持 BIGSERIAL 自增主键

**Schema Decisions**:
- 表名：`data_push_configuration`（与现有命名约定一致）
- **不存储推送状态和最近推送时间**：通过关联查询 `push_record` 表获取
- 启用状态字段：`enabled INT2`（用于控制推送开关，1=启用，0=停用）

#### API 设计
**Decision**: RESTful API with Spring MVC  
**Rationale**:
- 符合宪章 API 设计规范（章程 II. API Design）
- 使用标准 HTTP 方法：POST（创建）、GET（查询）、PUT（更新）
- 路径版本控制：`/api/v1/site-sync-configs`

**Endpoint Design**:
- POST `/api/v1/site-sync-configs` - 创建配置
- GET `/api/v1/site-sync-configs` - 分页查询列表（包含推送状态）
- GET `/api/v1/site-sync-configs/{id}` - 查询单个配置
- PUT `/api/v1/site-sync-configs/{id}` - 更新配置
- PUT `/api/v1/site-sync-configs/{id}/enable` - 启用配置
- PUT `/api/v1/site-sync-configs/{id}/disable` - 停用配置

#### 输入验证策略
**Decision**: Spring Validation + Custom Validators  
**Rationale**:
- 符合宪章安全要求（章程 V. Security）
- 格式验证在 Controller 层，业务规则验证在 Service 层

**Validation Rules**:
- 院区名称、院区标识、接口地址：非空、非空格
- 接口地址唯一性：数据库级别验证（UNIQUE 约束）

#### 事务管理
**Decision**: Service 层事务管理  
**Rationale**:
- 符合宪章事务管理要求（章程 IV. Transaction Management）
- 关键操作（创建、更新、启停用）使用 `@Transactional`
- 确保配置变更和审计日志记录的原子性

#### 审计日志记录
**Decision**: 调用项目统一审计日志服务  
**Rationale**:
- 使用项目统一的 `ICdpOpenApiService.addAuditLog()` 方法
- 符合宪章数据完整性要求（章程 IV. Data Integrity）
- 记录所有配置变更：创建、更新、启用、停用
- 包含操作类型、操作内容和操作状态

#### 推送状态查询优化
**Decision**: 左连接查询 + 子查询获取最新记录  
**Rationale**:
- 需要显示每个配置的最新推送状态和时间
- 使用子查询按 `config_id` 分组取最新 `push_time` 记录
- 避免 N+1 查询问题（符合宪章性能标准）

**SQL Pattern**:
```sql
SELECT 
    c.*,
    c.enabled as config_enabled,
    pr.push_time as last_push_time,
    pr.status as push_status
FROM data_push_configuration c
LEFT JOIN LATERAL (
    SELECT push_time, status
    FROM push_record
    WHERE config_id = c.id
    ORDER BY push_time DESC
    LIMIT 1
) pr ON true
WHERE ...
```

**Status Calculation Logic**:
```java
if (config.getEnabled() == 0) {
    return "已停用";
} else if (pushStatus == null) {
    return null;  // 无推送记录
} else if ("SUCCESS".equals(pushStatus)) {
    return "实时推送中";
} else if ("FAILED".equals(pushStatus)) {
    return "推送异常（重试中）";
}
```

#### 测试策略
**Decision**: Test-First Development (TDD)  
**Rationale**:
- 符合宪章强制要求（章程 III. Test-First Development NON-NEGOTIABLE）
- 测试覆盖率目标 ≥90%

**Test Layers**:
1. **单元测试**：Service 层业务逻辑
   - Mock Mapper 层依赖
   - 验证唯一性检查、状态计算逻辑

## 未知项解决方案

### 1. 如何确保接口地址唯一性（并发冲突）？

**背景**：边界情况提到"多个管理员同时创建具有相同接口地址的配置"

**Research**:
- 通过代码在新增或修改前，先查询所有配置，判断新创建或修改的接口地址是否已存在。
- 如果存在，则直接抛出异常并提示“接口地址重复”。
- 不依赖数据库唯一约束，全部由应用层控制，便于自定义错误提示。

**Decision**:
- 新建或修改配置时，先通过代码查询所有配置的接口地址。
- 若发现已存在相同的接口地址（排除本次修改的自身），则抛出业务异常，提示“接口地址重复”。
- 不再依赖数据库唯一约束兜底。

**Implementation**:
```java
// 新建或修改配置时，先查所有配置
List<DataPushConfiguration> allConfigs = configMapper.selectAll();
boolean exists = allConfigs.stream()
    .anyMatch(cfg -> cfg.getTargetUrl().equals(newConfig.getTargetUrl())
        && !Objects.equals(cfg.getId(), newConfig.getId()));
if (exists) {
    throw new BusinessException("接口地址重复");
}
// ...后续插入或更新逻辑
```

## 最佳实践应用

### Spring Boot 最佳实践
- **构造器注入**：Service 依赖通过构造器注入（章程禁止字段注入）
- **配置外部化**：推送相关配置放在 `application.yml`
- **Health Check**：添加 Actuator 健康检查端点

### MyBatis 最佳实践
- **参数化查询**：防止 SQL 注入（章程 V. Security）
- **ResultMap 复用**：定义可复用的 ResultMap
- **分页查询**：使用 PageHelper 插件

### 安全最佳实践
- **输入验证**：所有外部输入验证（章程 V. Security）
- **SQL 注入防护**：使用 `#{参数}` 而非 `${参数}`

### 监控和日志
- **结构化日志**：记录请求 ID、用户 ID、操作类型
- **性能监控**：关键操作记录执行时间
- **异常追踪**：完整堆栈 + 业务上下文

## 风险和缓解措施

### 风险 1：并发更新冲突
**Impact**: 多个管理员同时编辑同一配置，可能出现数据覆盖  
**Mitigation**:
- 使用乐观锁（`version` 字段）
- 更新时检查版本号，不匹配则拒绝

### 风险 2：性能问题（列表查询）
**Impact**: 关联 push_record 查询可能较慢  
**Mitigation**:
- 使用 LATERAL 子查询优化
- 添加索引：`idx_push_record_config_id_push_time` (config_id, push_time DESC)
- 分页查询限制每页记录数

## 技术债务和后续优化

### 潜在优化点
1. **缓存推送状态**：使用 Caffeine 缓存最新推送记录，减少数据库查询
2. **配置变更历史**：实现配置版本管理，支持回滚
3. **批量操作**：支持批量启用/停用配置
4. **推送状态实时更新**：使用 WebSocket 推送状态变更通知

### 遗留问题
- 推送服务的具体实现细节待其他需求澄清
- 审计日志的查询和展示功能未包含在本需求中

## 参考资料

### 内部文档
- [Smart QC Service Constitution](../../.specify/memory/constitution.md)
- [功能规范](./spec.md)

### 外部资源
- [Spring Boot Best Practices](https://spring.io/guides)
- [MyBatis Documentation](https://mybatis.org/mybatis-3/)
- [PostgreSQL Lateral Subqueries](https://www.postgresql.org/docs/current/queries-table-expressions.html#QUERIES-LATERAL)
