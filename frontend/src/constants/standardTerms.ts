export const TERMS = {
  graphEntityEnName: '实体落地英文表名',
  graphEntityCnName: '实体中文名称',
  graphEntityDesc: '图谱实体描述',
  entityFieldEnName: '实体字段英文名',
  entityFieldCnName: '实体字段中文名',
  sourceBizSystem: '来源业务系统',
  sourceTableEnName: '来源表英文名',
  sourceTableCnName: '来源表中文名',
  sourceFieldEnName: '来源字段英文名称',
  sourceFieldCnName: '来源字段中文名称',
  extractionLogic: '取数逻辑说明',
  mappingRule: '映射规则',
  mappingRuleConfig: '映射规则配置',
  mappingInfoView: '映射信息查看',
  sourceTableCatalog: '来源表目录',
  sourceFieldCatalog: '来源字段目录',
};

export const MAPPING_TEMPLATE_HEADERS = [
  `${TERMS.graphEntityEnName}(代码)`,
  '实体落地英文表名',
  TERMS.entityFieldEnName,
  TERMS.sourceTableEnName,
  `${TERMS.sourceFieldEnName}(多个用|分隔)`,
  TERMS.extractionLogic,
  'SQL内容',
];

export const SOURCE_TABLE_TEMPLATE_HEADERS = {
  master: `序号,专业,部署方式,系统名称,系统编码,L1-主数据,L2-主数据对象,${TERMS.sourceTableEnName},${TERMS.sourceTableCnName},表类型`,
  business: `序号,专业,部署方式,系统名称,系统编码,L3-业务模块,L4-业务活动对象,${TERMS.sourceTableEnName},${TERMS.sourceTableCnName},表类型,关联主数据大类,关联主数据小类`,
  reference: `序号,专业,部署方式,系统名称,系统编码,参考数据分类,${TERMS.sourceTableEnName},${TERMS.sourceTableCnName},表类型`,
  fields: `序号,${TERMS.sourceTableCnName},${TERMS.sourceTableEnName},来源系统编码,库表定义,${TERMS.sourceFieldCnName},${TERMS.sourceFieldEnName},字段描述,数据类型,长度/精度,小数位,主/外键,是否参考数据,参考数据引用说明,参考数据调用说明,是否建历史表,修改状态,修改时间,变更原因,应用范围`,
};
