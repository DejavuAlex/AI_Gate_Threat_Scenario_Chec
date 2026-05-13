# Business Flow

1. 开发人员在 Speckit 阶段编写业务需求文档。
2. 开发人员上传相关文档附件。
3. 开发人员或 CI 触发 Gate1 review。
4. 系统读取 Gate1 金标准知识库并匹配业务威胁场景。
5. 系统生成 Security-Review-Gate1.md。
6. 安全 reviewer 在 UI 中人工检查、修改并 approve。
7. 架构和 API 文档完成后触发 Gate2 review。
8. 系统验证 Gate1 安全控制措施是否在技术文档中落实。
