# iwiki-service


**简介**:iwiki-service


**HOST**:http://192.168.56.1:9022/api/v1


**联系人**:shanghai.cdp-support@roche.com


**Version**:0.2.0


**接口路径**:/api/v1/v3/api-docs/default


[TOC]






# Profile相关Api


## 分页列表查询


**接口地址**:`/api/v1/profile`


**请求方式**:`GET`


**请求数据类型**:`application/x-www-form-urlencoded`


**响应数据类型**:`*/*`


**接口描述**:


**请求参数**:


| 参数名称 | 参数说明 | 请求类型    | 是否必须 | 数据类型 | schema |
| -------- | -------- | ----- | -------- | -------- | ------ |
|profileName|质控参数名称|query|false|string||
|systemTestItemAbbreviation|系统检测项目缩写|query|false|string||
|startCreateTime|创建开始时间格式yyyy-MM-dd|query|false|string||
|endCreateTime|创建结束时间格式yyyy-MM-dd|query|false|string||
|pageNum|当前第几页|query|false|int||
|pageSize|每页记录数|query|false|int||
|sortColumn|排序字段|query|false|String||
|sortType|排序方式【ASC正序，DESC倒叙】|query|false|String||


**响应状态**:


| 状态码 | 说明 | schema |
| -------- | -------- | ----- |
|200|OK|ResultPageResponseVoProfileVo|


**响应参数**:


| 参数名称 | 参数说明 | 类型 | schema |
| -------- | -------- | ----- |----- |
|code|响应码 0-成功；其他值-失败|integer(int32)|integer(int32)|
|payload||PageResponseVoProfileVo|PageResponseVoProfileVo|
|&emsp;&emsp;data|响应VO|array|ProfileVo|
|&emsp;&emsp;&emsp;&emsp;id|主键|integer||
|&emsp;&emsp;&emsp;&emsp;profileName|质控参数名称|string||
|&emsp;&emsp;&emsp;&emsp;taskId|任务Id|integer||
|&emsp;&emsp;&emsp;&emsp;calculationResultId|计算结果Id|integer||
|&emsp;&emsp;&emsp;&emsp;systemTestItemChineseName|系统检测项目缩写|string||
|&emsp;&emsp;&emsp;&emsp;systemTestItemAbbreviation|系统检测项目缩写|string||
|&emsp;&emsp;&emsp;&emsp;triggerPoint|trigger point|integer||
|&emsp;&emsp;&emsp;&emsp;dataTransformedType|数据对称转换|string||
|&emsp;&emsp;&emsp;&emsp;dataTransformValue|数据对称转换值|number||
|&emsp;&emsp;&emsp;&emsp;calculationFormula|计算公式名称|string||
|&emsp;&emsp;&emsp;&emsp;windowPeriodValue|窗口期值|integer||
|&emsp;&emsp;&emsp;&emsp;targetValue|靶值|number||
|&emsp;&emsp;&emsp;&emsp;errorMax|误差上线|number||
|&emsp;&emsp;&emsp;&emsp;errorMin|误差下限|number||
|&emsp;&emsp;&emsp;&emsp;alarmMax|报警上限|number||
|&emsp;&emsp;&emsp;&emsp;alarmMin|报警下限|number||
|&emsp;&emsp;&emsp;&emsp;standardDeviation|标准差|number||
|&emsp;&emsp;&emsp;&emsp;weight|权重|number||
|&emsp;&emsp;&emsp;&emsp;truncationValueMax|截断值上限|number||
|&emsp;&emsp;&emsp;&emsp;truncationValueMin|截断值下限|number||
|&emsp;&emsp;&emsp;&emsp;creator|创建人|string||
|&emsp;&emsp;&emsp;&emsp;createTime|创建时间|string||
|&emsp;&emsp;&emsp;&emsp;updateTime|更新时间|string||
|&emsp;&emsp;&emsp;&emsp;updater|更新人|string||
|&emsp;&emsp;&emsp;&emsp;applications|分页-响应model|array|ProfileApplicationVo|
|&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;parameterId|应用参数id|integer||
|&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;applicationName|应用名称|string||
|&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;status|状态 0未启用 1启用|integer||
|&emsp;&emsp;total|总记录数|integer(int64)||
|&emsp;&emsp;pages|总页数|integer(int64)||
|&emsp;&emsp;pageNum|当前第几页|integer(int64)||
|&emsp;&emsp;pageSize|每页记录数|integer(int64)||
|errorMessage|响应说明|string||


**响应示例**:
```javascript
{
	"code": 0,
	"payload": {
		"data": [
			{
				"id": 0,
				"profileName": "",
				"taskId": 0,
				"calculationResultId": 0,
				"systemTestItemChineseName": "",
				"systemTestItemAbbreviation": "",
				"triggerPoint": 0,
				"dataTransformedType": "",
				"dataTransformValue": 0,
				"calculationFormula": "",
				"windowPeriodValue": 0,
				"targetValue": 0,
				"errorMax": 0,
				"errorMin": 0,
				"alarmMax": 0,
				"alarmMin": 0,
				"standardDeviation": 0,
				"weight": 0,
				"truncationValueMax": 0,
				"truncationValueMin": 0,
				"creator": "",
				"createTime": "",
				"updateTime": "",
				"updater": "",
				"applications": [
					{
						"parameterId": 0,
						"applicationName": "",
						"status": 0
					}
				]
			}
		],
		"total": 0,
		"pages": 0,
		"pageNum": 0,
		"pageSize": 0
	},
	"errorMessage": ""
}
```


## 添加返回新增后的id


**接口地址**:`/api/v1/profile`


**请求方式**:`POST`


**请求数据类型**:`application/x-www-form-urlencoded,application/json`


**响应数据类型**:`*/*`


**接口描述**:


**请求示例**:


```javascript
{
  "id": 0,
  "profileName": "",
  "taskId": 0,
  "calculationResultId": 0,
  "systemTestItemChineseName": "",
  "systemTestItemAbbreviation": "",
  "triggerPoint": 0,
  "dataTransformedType": "",
  "dataTransformValue": 0,
  "calculationFormula": "",
  "windowPeriodValue": 0,
  "targetValue": 0,
  "errorMax": 0,
  "errorMin": 0,
  "alarmMax": 0,
  "alarmMin": 0,
  "standardDeviation": 0,
  "weight": 0,
  "truncationValueMax": 0,
  "truncationValueMin": 0
}
```


**请求参数**:


| 参数名称 | 参数说明 | 请求类型    | 是否必须 | 数据类型 | schema |
| -------- | -------- | ----- | -------- | -------- | ------ |
|profileDto|profileDto|body|true|ProfileDto|ProfileDto|
|&emsp;&emsp;id|主键||false|integer(int64)||
|&emsp;&emsp;profileName|质控参数名称||false|string||
|&emsp;&emsp;taskId|任务Id||false|integer(int64)||
|&emsp;&emsp;calculationResultId|计算结果Id||false|integer(int64)||
|&emsp;&emsp;systemTestItemChineseName|系统检测项目缩写||false|string||
|&emsp;&emsp;systemTestItemAbbreviation|系统检测项目缩写||false|string||
|&emsp;&emsp;triggerPoint|trigger point||false|integer(int32)||
|&emsp;&emsp;dataTransformedType|数据对称转换||false|string||
|&emsp;&emsp;dataTransformValue|数据对称转换值||false|number||
|&emsp;&emsp;calculationFormula|计算公式名称||false|string||
|&emsp;&emsp;windowPeriodValue|窗口期值||false|integer(int32)||
|&emsp;&emsp;targetValue|靶值||false|number||
|&emsp;&emsp;errorMax|误差上线||false|number||
|&emsp;&emsp;errorMin|误差下限||false|number||
|&emsp;&emsp;alarmMax|报警上限||false|number||
|&emsp;&emsp;alarmMin|报警下限||false|number||
|&emsp;&emsp;standardDeviation|标准差||false|number||
|&emsp;&emsp;weight|权重||false|number||
|&emsp;&emsp;truncationValueMax|截断值上限||false|number||
|&emsp;&emsp;truncationValueMin|截断值下限||false|number||


**响应状态**:


| 状态码 | 说明 | schema |
| -------- | -------- | ----- |
|200|OK|ResultLong|


**响应参数**:


| 参数名称 | 参数说明 | 类型 | schema |
| -------- | -------- | ----- |----- |
|code|响应码 0-成功；其他值-失败|integer(int32)|integer(int32)|
|payload|挂载数据|integer(int64)|integer(int64)|
|errorMessage|响应说明|string||


**响应示例**:
```javascript
{
	"code": 0,
	"payload": 0,
	"errorMessage": ""
}
```


## 编辑(先删除后新增)返回新增后的id


**接口地址**:`/api/v1/profile`


**请求方式**:`PUT`


**请求数据类型**:`application/x-www-form-urlencoded,application/json`


**响应数据类型**:`*/*`


**接口描述**:


**请求示例**:


```javascript
{
  "id": 0,
  "profileName": "",
  "taskId": 0,
  "calculationResultId": 0,
  "systemTestItemChineseName": "",
  "systemTestItemAbbreviation": "",
  "triggerPoint": 0,
  "dataTransformedType": "",
  "dataTransformValue": 0,
  "calculationFormula": "",
  "windowPeriodValue": 0,
  "targetValue": 0,
  "errorMax": 0,
  "errorMin": 0,
  "alarmMax": 0,
  "alarmMin": 0,
  "standardDeviation": 0,
  "weight": 0,
  "truncationValueMax": 0,
  "truncationValueMin": 0
}
```


**请求参数**:


| 参数名称 | 参数说明 | 请求类型    | 是否必须 | 数据类型 | schema |
| -------- | -------- | ----- | -------- | -------- | ------ |
|profileDto|profileDto|body|true|ProfileDto|ProfileDto|
|&emsp;&emsp;id|主键||false|integer(int64)||
|&emsp;&emsp;profileName|质控参数名称||false|string||
|&emsp;&emsp;taskId|任务Id||false|integer(int64)||
|&emsp;&emsp;calculationResultId|计算结果Id||false|integer(int64)||
|&emsp;&emsp;systemTestItemChineseName|系统检测项目缩写||false|string||
|&emsp;&emsp;systemTestItemAbbreviation|系统检测项目缩写||false|string||
|&emsp;&emsp;triggerPoint|trigger point||false|integer(int32)||
|&emsp;&emsp;dataTransformedType|数据对称转换||false|string||
|&emsp;&emsp;dataTransformValue|数据对称转换值||false|number||
|&emsp;&emsp;calculationFormula|计算公式名称||false|string||
|&emsp;&emsp;windowPeriodValue|窗口期值||false|integer(int32)||
|&emsp;&emsp;targetValue|靶值||false|number||
|&emsp;&emsp;errorMax|误差上线||false|number||
|&emsp;&emsp;errorMin|误差下限||false|number||
|&emsp;&emsp;alarmMax|报警上限||false|number||
|&emsp;&emsp;alarmMin|报警下限||false|number||
|&emsp;&emsp;standardDeviation|标准差||false|number||
|&emsp;&emsp;weight|权重||false|number||
|&emsp;&emsp;truncationValueMax|截断值上限||false|number||
|&emsp;&emsp;truncationValueMin|截断值下限||false|number||


**响应状态**:


| 状态码 | 说明 | schema |
| -------- | -------- | ----- |
|200|OK|ResultLong|


**响应参数**:


| 参数名称 | 参数说明 | 类型 | schema |
| -------- | -------- | ----- |----- |
|code|响应码 0-成功；其他值-失败|integer(int32)|integer(int32)|
|payload|挂载数据|integer(int64)|integer(int64)|
|errorMessage|响应说明|string||


**响应示例**:
```javascript
{
	"code": 0,
	"payload": 0,
	"errorMessage": ""
}
```


## 验证是否存在


**接口地址**:`/api/v1/profile/verify`


**请求方式**:`POST`


**请求数据类型**:`application/x-www-form-urlencoded,application/json`


**响应数据类型**:`*/*`


**接口描述**:


**请求示例**:


```javascript
{
  "id": 0,
  "profileName": "",
  "taskId": 0,
  "calculationResultId": 0,
  "systemTestItemChineseName": "",
  "systemTestItemAbbreviation": "",
  "triggerPoint": 0,
  "dataTransformedType": "",
  "dataTransformValue": 0,
  "calculationFormula": "",
  "windowPeriodValue": 0,
  "targetValue": 0,
  "errorMax": 0,
  "errorMin": 0,
  "alarmMax": 0,
  "alarmMin": 0,
  "standardDeviation": 0,
  "weight": 0,
  "truncationValueMax": 0,
  "truncationValueMin": 0
}
```


**请求参数**:


| 参数名称 | 参数说明 | 请求类型    | 是否必须 | 数据类型 | schema |
| -------- | -------- | ----- | -------- | -------- | ------ |
|profileDto|profileDto|body|true|ProfileDto|ProfileDto|
|&emsp;&emsp;id|主键||false|integer(int64)||
|&emsp;&emsp;profileName|质控参数名称||false|string||
|&emsp;&emsp;taskId|任务Id||false|integer(int64)||
|&emsp;&emsp;calculationResultId|计算结果Id||false|integer(int64)||
|&emsp;&emsp;systemTestItemChineseName|系统检测项目缩写||false|string||
|&emsp;&emsp;systemTestItemAbbreviation|系统检测项目缩写||false|string||
|&emsp;&emsp;triggerPoint|trigger point||false|integer(int32)||
|&emsp;&emsp;dataTransformedType|数据对称转换||false|string||
|&emsp;&emsp;dataTransformValue|数据对称转换值||false|number||
|&emsp;&emsp;calculationFormula|计算公式名称||false|string||
|&emsp;&emsp;windowPeriodValue|窗口期值||false|integer(int32)||
|&emsp;&emsp;targetValue|靶值||false|number||
|&emsp;&emsp;errorMax|误差上线||false|number||
|&emsp;&emsp;errorMin|误差下限||false|number||
|&emsp;&emsp;alarmMax|报警上限||false|number||
|&emsp;&emsp;alarmMin|报警下限||false|number||
|&emsp;&emsp;standardDeviation|标准差||false|number||
|&emsp;&emsp;weight|权重||false|number||
|&emsp;&emsp;truncationValueMax|截断值上限||false|number||
|&emsp;&emsp;truncationValueMin|截断值下限||false|number||


**响应状态**:


| 状态码 | 说明 | schema |
| -------- | -------- | ----- |
|200|OK|ResultProfileVo|


**响应参数**:


| 参数名称 | 参数说明 | 类型 | schema |
| -------- | -------- | ----- |----- |
|code|响应码 0-成功；其他值-失败|integer(int32)|integer(int32)|
|payload||ProfileVo|ProfileVo|
|&emsp;&emsp;id|主键|integer(int64)||
|&emsp;&emsp;profileName|质控参数名称|string||
|&emsp;&emsp;taskId|任务Id|integer(int64)||
|&emsp;&emsp;calculationResultId|计算结果Id|integer(int64)||
|&emsp;&emsp;systemTestItemChineseName|系统检测项目缩写|string||
|&emsp;&emsp;systemTestItemAbbreviation|系统检测项目缩写|string||
|&emsp;&emsp;triggerPoint|trigger point|integer(int32)||
|&emsp;&emsp;dataTransformedType|数据对称转换|string||
|&emsp;&emsp;dataTransformValue|数据对称转换值|number||
|&emsp;&emsp;calculationFormula|计算公式名称|string||
|&emsp;&emsp;windowPeriodValue|窗口期值|integer(int32)||
|&emsp;&emsp;targetValue|靶值|number||
|&emsp;&emsp;errorMax|误差上线|number||
|&emsp;&emsp;errorMin|误差下限|number||
|&emsp;&emsp;alarmMax|报警上限|number||
|&emsp;&emsp;alarmMin|报警下限|number||
|&emsp;&emsp;standardDeviation|标准差|number||
|&emsp;&emsp;weight|权重|number||
|&emsp;&emsp;truncationValueMax|截断值上限|number||
|&emsp;&emsp;truncationValueMin|截断值下限|number||
|&emsp;&emsp;creator|创建人|string||
|&emsp;&emsp;createTime|创建时间|string(date-time)||
|&emsp;&emsp;updateTime|更新时间|string(date-time)||
|&emsp;&emsp;updater|更新人|string||
|&emsp;&emsp;applications|分页-响应model|array|ProfileApplicationVo|
|&emsp;&emsp;&emsp;&emsp;parameterId|应用参数id|integer||
|&emsp;&emsp;&emsp;&emsp;applicationName|应用名称|string||
|&emsp;&emsp;&emsp;&emsp;status|状态 0未启用 1启用|integer||
|errorMessage|响应说明|string||


**响应示例**:
```javascript
{
	"code": 0,
	"payload": {
		"id": 0,
		"profileName": "",
		"taskId": 0,
		"calculationResultId": 0,
		"systemTestItemChineseName": "",
		"systemTestItemAbbreviation": "",
		"triggerPoint": 0,
		"dataTransformedType": "",
		"dataTransformValue": 0,
		"calculationFormula": "",
		"windowPeriodValue": 0,
		"targetValue": 0,
		"errorMax": 0,
		"errorMin": 0,
		"alarmMax": 0,
		"alarmMin": 0,
		"standardDeviation": 0,
		"weight": 0,
		"truncationValueMax": 0,
		"truncationValueMin": 0,
		"creator": "",
		"createTime": "",
		"updateTime": "",
		"updater": "",
		"applications": [
			{
				"parameterId": 0,
				"applicationName": "",
				"status": 0
			}
		]
	},
	"errorMessage": ""
}
```


## 通过id查询


**接口地址**:`/api/v1/profile/{id}`


**请求方式**:`GET`


**请求数据类型**:`application/x-www-form-urlencoded`


**响应数据类型**:`*/*`


**接口描述**:


**请求参数**:


| 参数名称 | 参数说明 | 请求类型    | 是否必须 | 数据类型 | schema |
| -------- | -------- | ----- | -------- | -------- | ------ |
|id||path|true|integer(int64)||


**响应状态**:


| 状态码 | 说明 | schema |
| -------- | -------- | ----- |
|200|OK|ResultProfileVo|


**响应参数**:


| 参数名称 | 参数说明 | 类型 | schema |
| -------- | -------- | ----- |----- |
|code|响应码 0-成功；其他值-失败|integer(int32)|integer(int32)|
|payload||ProfileVo|ProfileVo|
|&emsp;&emsp;id|主键|integer(int64)||
|&emsp;&emsp;profileName|质控参数名称|string||
|&emsp;&emsp;taskId|任务Id|integer(int64)||
|&emsp;&emsp;calculationResultId|计算结果Id|integer(int64)||
|&emsp;&emsp;systemTestItemChineseName|系统检测项目缩写|string||
|&emsp;&emsp;systemTestItemAbbreviation|系统检测项目缩写|string||
|&emsp;&emsp;triggerPoint|trigger point|integer(int32)||
|&emsp;&emsp;dataTransformedType|数据对称转换|string||
|&emsp;&emsp;dataTransformValue|数据对称转换值|number||
|&emsp;&emsp;calculationFormula|计算公式名称|string||
|&emsp;&emsp;windowPeriodValue|窗口期值|integer(int32)||
|&emsp;&emsp;targetValue|靶值|number||
|&emsp;&emsp;errorMax|误差上线|number||
|&emsp;&emsp;errorMin|误差下限|number||
|&emsp;&emsp;alarmMax|报警上限|number||
|&emsp;&emsp;alarmMin|报警下限|number||
|&emsp;&emsp;standardDeviation|标准差|number||
|&emsp;&emsp;weight|权重|number||
|&emsp;&emsp;truncationValueMax|截断值上限|number||
|&emsp;&emsp;truncationValueMin|截断值下限|number||
|&emsp;&emsp;creator|创建人|string||
|&emsp;&emsp;createTime|创建时间|string(date-time)||
|&emsp;&emsp;updateTime|更新时间|string(date-time)||
|&emsp;&emsp;updater|更新人|string||
|&emsp;&emsp;applications|分页-响应model|array|ProfileApplicationVo|
|&emsp;&emsp;&emsp;&emsp;parameterId|应用参数id|integer||
|&emsp;&emsp;&emsp;&emsp;applicationName|应用名称|string||
|&emsp;&emsp;&emsp;&emsp;status|状态 0未启用 1启用|integer||
|errorMessage|响应说明|string||


**响应示例**:
```javascript
{
	"code": 0,
	"payload": {
		"id": 0,
		"profileName": "",
		"taskId": 0,
		"calculationResultId": 0,
		"systemTestItemChineseName": "",
		"systemTestItemAbbreviation": "",
		"triggerPoint": 0,
		"dataTransformedType": "",
		"dataTransformValue": 0,
		"calculationFormula": "",
		"windowPeriodValue": 0,
		"targetValue": 0,
		"errorMax": 0,
		"errorMin": 0,
		"alarmMax": 0,
		"alarmMin": 0,
		"standardDeviation": 0,
		"weight": 0,
		"truncationValueMax": 0,
		"truncationValueMin": 0,
		"creator": "",
		"createTime": "",
		"updateTime": "",
		"updater": "",
		"applications": [
			{
				"parameterId": 0,
				"applicationName": "",
				"status": 0
			}
		]
	},
	"errorMessage": ""
}
```


## 通过id删除


**接口地址**:`/api/v1/profile/{id}`


**请求方式**:`DELETE`


**请求数据类型**:`application/x-www-form-urlencoded`


**响应数据类型**:`*/*`


**接口描述**:


**请求参数**:


| 参数名称 | 参数说明 | 请求类型    | 是否必须 | 数据类型 | schema |
| -------- | -------- | ----- | -------- | -------- | ------ |
|id||path|true|integer(int64)||


**响应状态**:


| 状态码 | 说明 | schema |
| -------- | -------- | ----- |
|200|OK|ResultString|


**响应参数**:


| 参数名称 | 参数说明 | 类型 | schema |
| -------- | -------- | ----- |----- |
|code|响应码 0-成功；其他值-失败|integer(int32)|integer(int32)|
|payload|挂载数据|string||
|errorMessage|响应说明|string||


**响应示例**:
```javascript
{
	"code": 0,
	"payload": "",
	"errorMessage": ""
}
```


## 批量删除多个id用,隔开


**接口地址**:`/api/v1/profile/batch`


**请求方式**:`DELETE`


**请求数据类型**:`application/x-www-form-urlencoded`


**响应数据类型**:`*/*`


**接口描述**:


**请求参数**:


| 参数名称 | 参数说明 | 请求类型    | 是否必须 | 数据类型 | schema |
| -------- | -------- | ----- | -------- | -------- | ------ |
|ids||query|true|string||


**响应状态**:


| 状态码 | 说明 | schema |
| -------- | -------- | ----- |
|200|OK|ResultString|


**响应参数**:


| 参数名称 | 参数说明 | 类型 | schema |
| -------- | -------- | ----- |----- |
|code|响应码 0-成功；其他值-失败|integer(int32)|integer(int32)|
|payload|挂载数据|string||
|errorMessage|响应说明|string||


**响应示例**:
```javascript
{
	"code": 0,
	"payload": "",
	"errorMessage": ""
}
```