# 快速开始指南

**功能**：院区数据同步配置管理  
**分支**：sml-8241  
**创建时间**：2026年2月5日

## 概述

本指南提供院区数据同步配置管理功能的快速上手教程，帮助开发者理解整体开发流程和最佳实践。

## 开发流程

### 阶段 0：环境准备

#### 1. 切换到功能分支

```bash
cd smart-qc-service
git checkout -b feature/sml-8241-2.1.0
```

#### 2. 验证开发环境

```bash
# 验证 Java 版本
java -version  # 应显示 Java 17

# 验证 Maven 版本
mvn -版本  # 应显示 Maven 3.6+

# 验证 PostgreSQL 连接
psql -U your_user -d smartqc_db -c "SELECT version();"
```

#### 3. 更新依赖

```bash
cd smart-qc-service
mvn clean install -DskipTests
```

### 阶段 1：数据库迁移（Test-First）

#### 1.1 编写 Flyway 迁移脚本

**文件**：`src/main/resources/db/migration/V2.0.0.1__add_data_push_configuration.sql`

```sql
-- 参考 data-model.md 中的完整 DDL
CREATE TABLE data_push_configuration (
    id BIGSERIAL PRIMARY KEY,
    site_name VARCHAR(200) NOT NULL,
    site_id VARCHAR(200) NOT NULL,
    target_url VARCHAR(500) NOT NULL,
    enabled INT2 NOT NULL DEFAULT 1,
    create_time TIMESTAMP(0) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time TIMESTAMP(0) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator VARCHAR(255),
    updater VARCHAR(255),
    CONSTRAINT uk_target_url UNIQUE (target_url)
);

-- ... (其他索引)
```

#### 1.2 **先编写测试** - 验证迁移脚本

**文件**：`src/test/java/com/roche/smartqc/migration/V1_0_MigrationTest.java`

```java
package com.roche.smartqc.migration;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ActiveProfiles;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
@ActiveProfiles("test")
class V1_0_MigrationTest {
    
    @Autowired
    private JdbcTemplate jdbcTemplate;
    
    @Test
    void shouldCreateDataPushConfigurationTable() {
        // 验证表已创建
        Integer count = jdbcTemplate.queryForObject(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'data_push_configuration'",
            Integer.class
        );
        assertThat(count).isEqualTo(1);
    }
    
    @Test
    void shouldHaveUniqueConstraintOnTargetUrl() {
        // 验证唯一约束
        Integer count = jdbcTemplate.queryForObject(
            "SELECT COUNT(*) FROM information_schema.table_constraints " +
            "WHERE table_name = 'data_push_configuration' AND constraint_name = 'uk_target_url'",
            Integer.class
        );
        assertThat(count).isEqualTo(1);
    }
}
```

#### 1.3 运行迁移测试

```bash
mvn test -Dtest=V1_0_MigrationTest
```

**预期结果**：测试通过 ✅

### 阶段 2：领域模型开发（Test-First）

#### 2.1 **先编写测试** - 实体验证

**文件**：`src/test/java/com/roche/smartqc/domain/DataPushConfigurationTest.java`

```java
package com.roche.smartqc.domain;

import org.junit.jupiter.api.Test;
import static org.assertj.core.api.Assertions.assertThat;

class DataPushConfigurationTest {
    
    @Test
    void shouldCreateValidConfiguration() {
        DataPushConfiguration config = new DataPushConfiguration();
        config.setSiteName("北京分院");
        config.setSiteId("BJ-001");
        config.setTargetUrl("https://center.example.com/api");
        
        assertThat(config.getSiteName()).isEqualTo("北京分院");
        assertThat(config.getTargetUrl()).isNotBlank();
    }
}
```

#### 2.2 创建实体类

**文件**：`src/main/java/com/roche/smartqc/domain/DataPushConfiguration.java`

```java
// 参考 data-model.md 中的完整实体类定义
package com.roche.smartqc.domain;

import java.util.Date;

public class DataPushConfiguration {
    private Long id;
    private String siteName;
    private String siteId;
    private String targetUrl;
    private Integer enabled;
    private Date createTime;
    private Date updateTime;
    private String creator;
    private String updater;
    
    // Getters and Setters
}
```

#### 2.3 运行实体测试

```bash
mvn test -Dtest=DataPushConfigurationTest
```

### 阶段 3：Mapper 层开发（Test-First）

#### 3.1 **先编写测试** - Mapper 测试

**文件**：`src/test/java/com/roche/smartqc/mapper/DataPushConfigurationMapperTest.java`

```java
package com.roche.smartqc.mapper;

import com.roche.smartqc.domain.DataPushConfiguration;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.transaction.annotation.Transactional;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
@ActiveProfiles("test")
@Transactional
class DataPushConfigurationMapperTest {
    
    @Autowired
    private DataPushConfigurationMapper mapper;
    
    @Test
    void shouldInsertConfiguration() {
        DataPushConfiguration config = new DataPushConfiguration();
        config.setSiteName("北京分院");
        config.setSiteId("BJ-001");
        config.setTargetUrl("https://center.example.com/api/beijing");
        config.setEnabled(1);
        config.setCreator("admin");
        
        int rows = mapper.insert(config);
        
        assertThat(rows).isEqualTo(1);
        assertThat(config.getId()).isNotNull();
    }
    
    @Test
    void shouldFindById() {
        // 先插入测试数据
        DataPushConfiguration config = createTestConfig();
        mapper.insert(config);
        
        // 查询
        DataPushConfiguration found = mapper.findById(config.getId());
        
        assertThat(found).isNotNull();
        assertThat(found.getSiteName()).isEqualTo("北京分院");
    }
    
    @Test
    void shouldEnforceUniqueTargetUrl() {
        // 插入第一个配置
        DataPushConfiguration config1 = createTestConfig();
        config1.setTargetUrl("https://center.example.com/api/test");
        mapper.insert(config1);
        
        // 尝试插入相同 URL
        DataPushConfiguration config2 = createTestConfig();
        config2.setTargetUrl("https://center.example.com/api/test");
        
        assertThatThrownBy(() -> mapper.insert(config2))
            .isInstanceOf(DataIntegrityViolationException.class);
    }
    
    private DataPushConfiguration createTestConfig() {
        DataPushConfiguration config = new DataPushConfiguration();
        config.setSiteName("北京分院");
        config.setSiteId("BJ-001");
        config.setTargetUrl("https://center.example.com/api/" + System.currentTimeMillis());
        config.setEnabled(1);
        config.setCreator("admin");
        return config;
    }
}
```

#### 3.2 创建 Mapper 接口

**文件**：`src/main/java/com/roche/smartqc/mapper/DataPushConfigurationMapper.java`

```java
package com.roche.smartqc.mapper;

import com.roche.smartqc.domain.DataPushConfiguration;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

@Mapper
public interface DataPushConfigurationMapper {
    
    /**
     * 插入配置
     */
    int insert(DataPushConfiguration config);
    
    /**
     * 根据 ID 查询
     */
    DataPushConfiguration findById(@Param("id") Long id);
    
    /**
     * 分页查询列表（包含推送状态）
     */
    List<DataPushConfiguration> findAll(@Param("enabled") Integer enabled);
    
    /**
     * 更新配置
     */
    int update(DataPushConfiguration config);
    
    /**
     * 检查 URL 是否存在
     */
    boolean existsByTargetUrl(@Param("targetUrl") String targetUrl, @Param("excludeId") Long excludeId);
}
```

#### 3.3 创建 MyBatis XML 映射

**文件**：`src/main/resources/mapper/DataPushConfigurationMapper.xml`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN" 
  "http://mybatis.org/dtd/mybatis-3-mapper.dtd">

<mapper namespace="com.roche.smartqc.mapper.DataPushConfigurationMapper">
    
    <resultMap id="BaseResultMap" type="com.roche.smartqc.domain.DataPushConfiguration">
        <id column="id" property="id"/>
        <result column="site_name" property="siteName"/>
        <result column="site_id" property="siteId"/>
        <result column="target_url" property="targetUrl"/>
        <result column="enabled" property="enabled"/>
        <result column="creator" property="creator"/>
        <result column="create_time" property="createTime"/>
        <result column="update_time" property="updateTime"/>
    </resultMap>
    
    <insert id="insert" useGeneratedKeys="true" keyProperty="id">
        INSERT INTO data_push_configuration 
        (site_name, site_id, target_url, enabled, creator)
        VALUES (#{siteName}, #{siteId}, #{targetUrl}, #{enabled}, #{creator})
    </insert>
    
    <select id="findById" resultMap="BaseResultMap">
        SELECT * FROM data_push_configuration WHERE id = #{id}
    </select>
    
    <select id="findAll" resultMap="BaseResultMap">
        SELECT 
            c.*,
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
        <where>
            <if test="enabled != null">
                AND c.enabled = #{enabled}
            </if>
        </where>
        ORDER BY c.create_time DESC
    </select>
    
    <update id="update">
        UPDATE data_push_configuration
        SET site_name = #{siteName},
            site_id = #{siteId},
            target_url = #{targetUrl},
            update_time = CURRENT_TIMESTAMP
        WHERE id = #{id}
    </update>
    
    <select id="existsByTargetUrl" resultType="boolean">
        SELECT EXISTS(
            SELECT 1 FROM data_push_configuration 
            WHERE target_url = #{targetUrl}
            <if test="excludeId != null">
                AND id != #{excludeId}
            </if>
        )
    </select>
</mapper>
```

#### 3.4 运行 Mapper 测试

```bash
mvn test -Dtest=DataPushConfigurationMapperTest
```

### 阶段 4：Service 层开发（Test-First）

#### 4.1 **先编写测试** - Service 单元测试

**文件**：`src/test/java/com/roche/smartqc/service/DataPushConfigServiceTest.java`

```java
package com.roche.smartqc.service;

import com.roche.smartqc.domain.DataPushConfiguration;
import com.roche.smartqc.dto.CreateConfigRequest;
import com.roche.smartqc.exception.BusinessException;
import com.roche.smartqc.mapper.DataPushConfigurationMapper;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class DataPushConfigServiceTest {
    
    @Mock
    private DataPushConfigurationMapper mapper;
    
    @Mock
    private ICdpOpenApiService cdpOpenApiService;
    
    @InjectMocks
    private DataPushConfigService service;
    
    @Test
    void shouldCreateConfig() {
        // Arrange
        CreateConfigRequest request = new CreateConfigRequest();
        request.setSiteName("北京分院");
        request.setSiteId("BJ-001");
        request.setTargetUrl("https://center.example.com/api");
        
        when(mapper.existsByTargetUrl(any(), isNull())).thenReturn(false);
        when(mapper.insert(any())).thenReturn(1);
        
        // Act
        DataPushConfiguration result = service.createConfig(request, "admin");
        
        // Assert
        assertThat(result).isNotNull();
        verify(mapper).insert(any());
        verify(cdpOpenApiService).addAuditLog(any(), any(), any()); // 验证审计日志
    }
    
    @Test
    void shouldThrowExceptionWhenUrlDuplicate() {
        // Arrange
        CreateConfigRequest request = new CreateConfigRequest();
        request.setTargetUrl("https://center.example.com/api");
        
        when(mapper.existsByTargetUrl(any(), isNull())).thenReturn(true);
        
        // Act & Assert
        assertThatThrownBy(() -> service.createConfig(request, "admin"))
            .isInstanceOf(BusinessException.class)
            .hasMessageContaining("接口地址重复");
        
        verify(mapper, never()).insert(any());
    }
}
```

#### 4.2 创建 Service 实现

**文件**：`src/main/java/com/roche/smartqc/service/DataPushConfigService.java`

```java
package com.roche.smartqc.service;

import com.roche.smartqc.domain.DataPushConfiguration;
import com.roche.smartqc.dto.CreateConfigRequest;
import com.roche.smartqc.dto.UpdateConfigRequest;
import com.roche.smartqc.exception.BusinessException;
import com.roche.smartqc.mapper.DataPushConfigurationMapper;
import com.roche.smartlab.smartqc.enums.AuditLogOperTypeEnum;
import com.roche.smartlab.smartqc.enums.AuditLogStatusEnum;
import com.roche.smartlab.smartqc.service.ICdpOpenApiService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class DataPushConfigService {
    
    private final DataPushConfigurationMapper configMapper;
    private final ICdpOpenApiService cdpOpenApiService;
    private final ObjectMapper objectMapper;
    
    // 构造器注入（符合宪章要求）
    public DataPushConfigService(
            DataPushConfigurationMapper configMapper,
            ICdpOpenApiService cdpOpenApiService) {
        this.configMapper = configMapper;
        this.cdpOpenApiService = cdpOpenApiService;
        this.objectMapper = new ObjectMapper();
    }
    
    @Transactional
    public DataPushConfiguration createConfig(CreateConfigRequest request, String operator) {
        // 验证唯一性
        if (configMapper.existsByTargetUrl(request.getTargetUrl(), null)) {
            throw new BusinessException("接口地址重复");
        }
        
        // 创建配置
        DataPushConfiguration config = new DataPushConfiguration();
        config.setSiteName(request.getSiteName());
        config.setSiteId(request.getSiteId());
        config.setTargetUrl(request.getTargetUrl());
        config.setEnabled(1);
        config.setCreator(operator);
        
        configMapper.insert(config);
        
        // 记录审计日志
        recordAuditLog(AuditLogOperTypeEnum.CREATE, 
                       String.format("创建配置: %s (%s)", config.getSiteName(), config.getTargetUrl()),
                       AuditLogStatusEnum.SUCCESS);
        
        return config;
    }
    
    // 其他方法...
    
    /**
     * 记录审计日志
     */
    private void recordAuditLog(AuditLogOperTypeEnum operationType, 
                               String operationContent, 
                               AuditLogStatusEnum status) {
        cdpOpenApiService.addAuditLog(operationType, operationContent, status);
    }
}
```

#### 4.3 运行 Service 测试

```bash
mvn test -Dtest=DataPushConfigServiceTest
```

**覆盖率目标**：≥90% ✅

### 阶段 5：Controller 层开发（Test-First）

#### 5.1 **先编写测试** - Controller 测试

**文件**：`src/test/java/com/roche/smartqc/controller/SiteSyncConfigControllerTest.java`

```java
package com.roche.smartqc.controller;

import com.roche.smartqc.dto.CreateConfigRequest;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.transaction.annotation.Transactional;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
@Transactional
class SiteSyncConfigControllerTest {
    
    @Autowired
    private MockMvc mockMvc;
    
    @Test
    void shouldCreateConfig() throws Exception {
        String requestBody = """
            {
                "siteName": "北京分院",
                "siteId": "BJ-001",
                "targetUrl": "https://center.example.com/api"
            }
            """;
        
        mockMvc.perform(post("/api/v1/site-sync-configs")
                .contentType(MediaType.APPLICATION_JSON)
                .content(requestBody))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.id").exists())
                .andExpect(jsonPath("$.data.siteName").value("北京分院"));
    }
    
    @Test
    void shouldReturnErrorWhenUrlDuplicate() throws Exception {
        // 先创建一个配置
        createTestConfig();
        
        // 尝试创建重复 URL 的配置
        String requestBody = """
            {
                "siteName": "上海分院",
                "siteId": "SH-001",
                "targetUrl": "https://center.example.com/api"
            }
            """;
        
        mockMvc.perform(post("/api/v1/site-sync-configs")
                .contentType(MediaType.APPLICATION_JSON)
                .content(requestBody))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.success").value(false))
                .andExpect(jsonPath("$.message").value("接口地址重复"));
    }
}
```

#### 5.2 创建 Controller

**文件**：`src/main/java/com/roche/smartqc/controller/SiteSyncConfigController.java`

```java
package com.roche.smartqc.controller;

import com.roche.smartqc.dto.CreateConfigRequest;
import com.roche.smartqc.dto.ApiResponse;
import com.roche.smartqc.service.DataPushConfigService;
import org.springframework.http.HttpStatus;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import javax.validation.Valid;

@RestController
@RequestMapping("/api/v1/site-sync-configs")
@Validated
public class SiteSyncConfigController {
    
    private final DataPushConfigService configService;
    
    public SiteSyncConfigController(DataPushConfigService configService) {
        this.configService = configService;
    }
    
    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public ApiResponse createConfig(@Valid @RequestBody CreateConfigRequest request) {
        // 从 Security Context 获取当前用户
        String operator = getCurrentUser();
        
        var config = configService.createConfig(request, operator);
        
        return ApiResponse.success("配置创建成功", config);
    }
    
    // 其他端点...
}
```

#### 5.3 运行 Controller 测试

```bash
mvn test -Dtest=SiteSyncConfigControllerTest
```

### 阶段 6：覆盖率验证

#### 6.1 生成覆盖率报告

```bash
mvn jacoco:report
```

打开报告：`target/site/jacoco/index.html`

**验证覆盖率 ≥90%** ✅

### 阶段 7：代码审查检查清单

按照宪章要求验证：

- ✅ 所有单元测试通过
- ✅ 代码覆盖率 ≥90%
- ✅ 无编译警告
- ✅ 符合分层架构（Controller → Service → Mapper）
- ✅ 使用构造器注入（非字段注入）
- ✅ 事务管理在 Service 层
- ✅ 输入验证（Controller 层 + Service 层）
- ✅ SQL 参数化查询（防止注入）
- ✅ 审计日志记录
- ✅ API 文档已更新

### 阶段 8：提交代码

```bash
git add .
git commit -m "feat(sml-8241): 实现院区数据同步配置管理

- 创建数据库表 data_push_configuration
- 使用 ICdpOpenApiService.addAuditLog() 记录审计日志
- 实现 CRUD API 接口
- 实现启用/停用功能
- 添加审计日志记录
- 测试覆盖率 92%

关联 JIRA: SML-8241"

git push origin feature/sml-8241-2.1.0
```

## API 使用示例

### 1. 创建配置

```http
POST /api/v1/site-sync-configs
Content-Type: application/json
Authorization: Bearer <token>

{
  "siteName": "北京分院",
  "siteId": "BJ-001",
  "targetUrl": "https://center.example.com/api/beijing"
}
```

**响应**：

```json
{
  "success": true,
  "message": "配置创建成功",
  "data": {
    "id": 1,
    "siteName": "北京分院",
    "siteId": "BJ-001",
    "targetUrl": "https://center.example.com/api/beijing",
    "enabled": 1,
    "currentPushStatus": null,
    "lastPushTime": null,
    "createTime": "2026-02-05T10:00:00Z"
  }
}
```

### 2. 查询配置列表

```http
GET /api/v1/site-sync-configs?page=1&pageSize=20
Authorization: Bearer <token>
```

**响应**：

```json
{
  "success": true,
  "message": "查询成功",
  "data": {
    "list": [
      {
        "id": 1,
        "siteName": "北京分院",
        "siteId": "BJ-001",
        "targetUrl": "https://center.example.com/api/beijing",
        "enabled": 1,
        "currentPushStatus": "实时推送中",
        "lastPushTime": "2026-02-05T10:30:00Z",
        "createTime": "2026-02-05T10:00:00Z"
      }
    ],
    "pagination": {
      "total": 1,
      "page": 1,
      "pageSize": 20
    }
  }
}
```

### 3. 停用配置

```http
PUT /api/v1/site-sync-configs/1/disable
Authorization: Bearer <token>
```

**响应**：

```json
{
  "success": true,
  "message": "配置已停用",
  "data": {
    "id": 1,
    "enabled": 0,
    "currentPushStatus": "已停用"
  }
}
```

## 常见问题

### Q1：为什么不在配置表中存储推送状态？

**A**：推送状态是动态的，由 `push_record` 表的最新记录决定。避免数据冗余和同步问题。

### Q2：如何确保接口地址唯一性？

**A**：双重保障：
1. 数据库唯一约束（`UNIQUE uk_target_url`）
2. 应用层验证（Service 层检查）

### Q4：测试覆盖率如何达到 90%？

**A**：
- Mapper 层：使用 `@SpringBootTest` 测试
- Service 层：使用 Mockito 单元测试，Mock Mapper 依赖
- Controller 层：使用 `MockMvc` 测试

### Q5：如何调试 MyBatis SQL？

**A**：在 `application-local.yml` 中启用日志：

```yaml
logging:
  level:
    com.roche.smartqc.mapper: DEBUG
```

## 下一步

- [ ] 实现审计日志查询接口
- [ ] 添加性能监控指标
- [ ] 编写用户手册

## 参考资料

- [功能规范](./spec.md)
- [研究文档](./research.md)
- [数据模型](./data-model.md)
- [API 规范](./contracts/api-spec.yaml)
- [宪章文档](../../.specify/memory/constitution.md)
