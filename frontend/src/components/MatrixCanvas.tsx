import React, { useEffect, useState, useRef, useMemo } from 'react';
import { Table, Checkbox, Spin, Empty, Typography, Tooltip, message, Space, Select, Modal, Form, Input, Button, Row, Col } from 'antd';
import { EditOutlined } from '@ant-design/icons';
import { StatusTag } from './shell';
import { conceptApi, entityApi, entityRelationManagerApi } from '../services/api';
import { useStore } from '../store/useStore';

const { Text } = Typography;

const MatrixCanvas: React.FC = () => {
  const { fetchConcepts, setRelationHighlight } = useStore();
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<any>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [tableHeight, setTableHeight] = useState<number>(0);
  // 筛选
  const [l0Filter, setL0Filter] = useState<string | undefined>();
  const [l1Filter, setL1Filter] = useState<string | undefined>();
  const [l3Filter, setL3Filter] = useState<string | undefined>();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  // 打点关系编辑（资产矩阵 <-> 实体关系管理 同源）
  const [editOpen, setEditOpen] = useState(false);
  const [editRelationId, setEditRelationId] = useState<string>('');
  const [editMasterEntity, setEditMasterEntity] = useState<any>(null);
  const [editActivityEntity, setEditActivityEntity] = useState<any>(null);
  const [editForm] = Form.useForm();

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await conceptApi.getGraphMatrix();
      setData(res.data.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // 动态计算表格可用高度
  const headerHeightRef = useRef<number>(0);
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const updateHeight = () => {
      const containerHeight = el.clientHeight;
      const headerEl = el.querySelector('.ant-table-header');
      const headerHeight = headerEl ? (headerEl as HTMLElement).offsetHeight : 0;
      if (headerHeight > 0) {
        headerHeightRef.current = headerHeight;
        const h = containerHeight - headerHeight - 2;
        setTableHeight(h > 200 ? h : 300);
      } else if (headerHeightRef.current === 0) {
        setTableHeight(containerHeight - 60);
      } else {
        const h = containerHeight - headerHeightRef.current - 2;
        setTableHeight(h > 200 ? h : 300);
      }
    };
    const ro = new ResizeObserver(updateHeight);
    ro.observe(el);
    const mo = new MutationObserver(updateHeight);
    mo.observe(el, { childList: true, subtree: true });
    const timer = setTimeout(updateHeight, 50);
    window.addEventListener('resize', updateHeight);
    return () => {
      clearTimeout(timer);
      window.removeEventListener('resize', updateHeight);
      ro.disconnect();
      mo.disconnect();
    };
  }, [loading, data]);

  const handleToggle = async (e: any, entityId: string, targetEntityId: string) => {
    e.stopPropagation();
    try {
      setData((prev: any) => {
        if (!prev) return prev;
        return {
          ...prev,
          rows: prev.rows.map((row: any) => ({
            ...row,
            entities: row.entities.map((ent: any) => {
              if (ent.id === entityId) {
                const ids = ent.linked_entity_ids || [];
                const isLinked = ids.includes(targetEntityId);
                return {
                  ...ent,
                  linked_entity_ids: isLinked
                    ? ids.filter((id: string) => id !== targetEntityId)
                    : [...ids, targetEntityId]
                };
              }
              return ent;
            })
          }))
        };
      });
      const res = await entityApi.toggleMatrixLink(entityId, targetEntityId);
      if (res.data?.action === 'linked' && res.data?.link_id) {
        setRelationHighlight({
          linkId: res.data.link_id,
          masterEntityId: targetEntityId,
          activityEntityId: entityId,
        });
      } else if (res.data?.action === 'unlinked') {
        setRelationHighlight(null);
      }
      await fetchData();
      fetchConcepts();
    } catch (err) {
      message.error('保存关联失败');
      fetchData();
    }
  };

  // 打开打点关系编辑窗：从 linked_entity_map 取该单元格对应关系详情预填
  const openMatrixEdit = (record: any, colEntity: any) => {
    const detail = record.linked_entity_map?.[colEntity.id];
    if (!detail) {
      message.warning('该打点关系详情缺失，请刷新后重试');
      return;
    }
    setEditRelationId(detail.id);
    setEditMasterEntity(colEntity); // 列实体 = 主数据 L2
    setEditActivityEntity({ id: record.id, name: record.entityRawName, code: record.entityCode }); // 行实体 = 业务活动 L4
    editForm.setFieldsValue({
      relation_name: detail.relation_name,
      cardinality: detail.cardinality || 'N:N',
      direction: detail.direction || 'forward',
      source_field_name: detail.source_field_name,
      target_field_name: detail.target_field_name,
      join_expr: detail.join_expr,
      remark: detail.remark,
    });
    setEditOpen(true);
  };

  const handleEditSave = async () => {
    try {
      const values = await editForm.validateFields();
      await entityRelationManagerApi.updateItem(editRelationId, {
        relation_group: 'master_activity',
        source_entity_id: editMasterEntity.id,
        target_entity_id: editActivityEntity.id,
        relation_category: '打点维护',
        relation_name: values.relation_name,
        direction: values.direction,
        cardinality: values.cardinality,
        source_field_name: values.source_field_name,
        target_field_name: values.target_field_name,
        join_expr: values.join_expr,
        remark: values.remark,
      });
      message.success('关系详情已更新');
      setEditOpen(false);
      fetchData();
      fetchConcepts();
    } catch (error: any) {
      if (error?.errorFields) return;
      message.error(error?.response?.data?.detail || '关系更新失败');
    }
  };

  if (loading && !data) return (
    <div style={{ padding: 100, textAlign: 'center' }}>
      <Spin size="large" tip="加载矩阵数据中...">
        <div style={{ minHeight: 200 }} />
      </Spin>
    </div>
  );
  if (!data) return <Empty description="暂无矩阵数据" />;

  const { columns, rows } = data;

  // L1 筛选选项（横向主数据）
  const l1Options = (columns.filter((c: any) => c.level === 1) || []).map((l1: any) => ({
    label: l1.name, value: l1.id,
  }));

  // L0 业务域 / L3 业务活动 筛选选项（纵向）
  const { domains = [] } = data;
  const l0Options = domains.map((dom: any) => ({ label: dom.name, value: dom.id }));
  const l3Options: any[] = [];
  domains.forEach((dom: any) => {
    const domL3 = rows.filter((r: any) => r.level === 3 && r.parent_id === dom.id);
    domL3.forEach((l3: any) => {
      l3Options.push({ label: `${dom.name} / ${l3.name}`, value: l3.id });
    });
  });

  // 构造 Table columns（左侧两列 fixed）
  const tableColumns: any[] = [
    {
      title: '业务活动层级',
      dataIndex: 'name',
      key: 'name',
      width: 220,
      fixed: 'left',
      render: (text: string, record: any) => (
        <div>
          <div style={{ fontWeight: record.level === 0 || record.level === 3 ? 'bold' : 'normal', color: record.level === 3 ? 'var(--color-primary)' : record.level === 0 ? 'var(--color-ai)' : 'inherit' }}>
            {record.level === 0 ? `[业务域] ${text}` : record.level === 3 ? `[L3] ${text}` : record.level === 4 ? <span style={{ paddingLeft: 16 }}>[L4] {text}</span> : text}
          </div>
        </div>
      )
    },
    {
      title: '数据实体',
      dataIndex: 'entityName',
      key: 'entityName',
      width: 180,
      fixed: 'left',
      render: (text: string, record: any) => record.type === 'entity' ? (
        <Tooltip title={record.entityCode}>
          <div style={{ lineHeight: '1.2' }}>
            <Text strong style={{ fontSize: '12px' }}>{record.entityRawName}</Text>
            <br/>
            <Text type="secondary" style={{ fontSize: '11px' }}>{record.entityCode}</Text>
          </div>
        </Tooltip>
      ) : '-'
    }
  ];

  // 横向列：按 L1 筛选过滤
  const l1List = columns.filter((c: any) => c.level === 1 && (!l1Filter || c.id === l1Filter));
  l1List.forEach((l1: any) => {
    const l2Children = columns.filter((c: any) => c.level === 2 && c.parent_id === l1.id);
    if (l2Children.length > 0) {
      const l2Cols = l2Children.map((l2: any) => {
        const allL2Entities = l2.entities || [];
        const entitySubCols = allL2Entities.map((ent: any) => ({
          title: (
            <Tooltip title={ent.code}>
              <div style={{ fontSize: '11px', whiteSpace: 'nowrap' }}>
                {ent.name} {ent.is_main_table && <StatusTag preset="info" style={{ fontSize: '10px', padding: '0 3px' }}>主</StatusTag>}
              </div>
            </Tooltip>
          ),
          dataIndex: `ent_${ent.id}`,
          key: ent.id,
          align: 'center',
          width: 120,
          ellipsis: true,
          render: (_: any, record: any) => {
            if (record.type !== 'entity') return null;
            const isLinked = record.linked_entity_ids?.includes(ent.id);
            return (
              <Space size={2}>
                <Checkbox
                  checked={isLinked}
                  onChange={(ev) => handleToggle(ev, record.id, ent.id)}
                />
                {isLinked && (
                  <Button
                    size="small"
                    type="link"
                    icon={<EditOutlined />}
                    onClick={() => openMatrixEdit(record, ent)}
                    style={{ padding: '0 4px' }}
                  />
                )}
              </Space>
            );
          }
        }));
        return {
          title: (
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '12px', fontWeight: 'bold' }}>{l2.name}</div>
            </div>
          ),
          children: entitySubCols.length > 0 ? entitySubCols : [{
            title: '-', width: 80, render: () => <div style={{ color: 'var(--border-color)', fontSize: '11px' }}>无实体</div>
          }]
        };
      });
      tableColumns.push({
        title: l1.name,
        children: l2Cols
      });
    }
  });

  // 展平数据用于 Table（纵向：L0->L3->L4->实体）
  const dataSource: any[] = [];
  const filteredDomains = l0Filter ? domains.filter((d: any) => d.id === l0Filter) : domains;
  filteredDomains.forEach((dom: any) => {
    const domL3 = rows.filter((r: any) => r.level === 3 && r.parent_id === dom.id);
    const filteredL3 = l3Filter ? domL3.filter((l3: any) => l3.id === l3Filter) : domL3;
    if (filteredL3.length === 0) return;
    dataSource.push({
      key: `dom_${dom.id}`,
      id: dom.id, name: dom.name, level: 0, type: 'domain'
    });
    filteredL3.forEach((l3: any) => {
      dataSource.push({
        key: `l3_${l3.id}`, id: l3.id, name: l3.name, level: 3, type: 'concept'
      });
      const l3L4 = rows.filter((r: any) => r.level === 4 && r.parent_id === l3.id);
      l3L4.forEach((l4: any) => {
        dataSource.push({
          key: `l4_${l4.id}`, id: l4.id, name: l4.name, level: 4, type: 'concept'
        });
        (l4.entities || []).forEach((ent: any) => {
          dataSource.push({
            key: `ent_${ent.id}`, id: ent.id, name: l4.name, level: 4,
            entityRawName: ent.name, entityCode: ent.code, en_name: ent.en_name,
            entityName: `${ent.name} (${ent.code})`, type: 'entity',
            linked_entity_ids: ent.linked_entity_ids || [],
            linked_entity_map: ent.linked_entity_map || {}
          });
        });
      });
    });
  });

  // 孤立 L3（无业务域）
  const orphanL3 = rows.filter((r: any) => r.level === 3 && (!r.parent_id || !domains.some((d: any) => d.id === r.parent_id)));
  const filteredOrphanL3 = l3Filter ? orphanL3.filter((l3: any) => l3.id === l3Filter) : orphanL3;
  if (!l0Filter && filteredOrphanL3.length > 0) {
    dataSource.push({ key: 'dom_orphan', name: '其他业务', level: 0, type: 'domain' });
    filteredOrphanL3.forEach((l3: any) => {
      dataSource.push({ key: `l3_${l3.id}`, id: l3.id, name: l3.name, level: 3, type: 'concept' });
      const l3L4 = rows.filter((r: any) => r.level === 4 && r.parent_id === l3.id);
      l3L4.forEach((l4: any) => {
        dataSource.push({ key: `l4_${l4.id}`, id: l4.id, name: l4.name, level: 4, type: 'concept' });
        (l4.entities || []).forEach((ent: any) => {
          dataSource.push({
            key: `ent_${ent.id}`, id: ent.id, name: l4.name, level: 4,
            entityRawName: ent.name, entityCode: ent.code, en_name: ent.en_name,
            entityName: `${ent.name} (${ent.code})`, type: 'entity',
            linked_entity_ids: ent.linked_entity_ids || [],
            linked_entity_map: ent.linked_entity_map || {}
          });
        });
      });
    });
  }

  // 计算总宽度
  const calcColWidth = (col: any): number => {
    if (col.children?.length) {
      return col.children.reduce((s: number, c: any) => s + calcColWidth(c), 0);
    }
    return col.width || 100;
  };
  const scrollX = tableColumns.reduce((sum, col) => sum + calcColWidth(col), 0);

  // 分页
  const pagedDataSource = dataSource.slice((page - 1) * pageSize, page * pageSize);

  return (
    <div style={{ height: '100%', padding: '8px 12px', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
      <div style={{ marginBottom: 8, display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0, flexWrap: 'wrap', gap: 8 }}>
        <Space size="middle" wrap>
          <Select
            allowClear
            placeholder="筛选主数据L1"
            value={l1Filter}
            onChange={(v) => { setL1Filter(v); setPage(1); }}
            options={l1Options}
            style={{ width: 160 }}
          />
          <Select
            allowClear
            placeholder="筛选业务域"
            value={l0Filter}
            onChange={(v) => { setL0Filter(v); setPage(1); }}
            options={l0Options}
            style={{ width: 140 }}
          />
          <Select
            allowClear
            placeholder="筛选业务活动L3"
            value={l3Filter}
            onChange={(v) => { setL3Filter(v); setPage(1); }}
            options={l3Options}
            style={{ width: 220 }}
            showSearch
            optionFilterProp="label"
          />
          <Text type="secondary" style={{ fontSize: 12 }}>
            共 {dataSource.length} 行 | 第 {page} 页
          </Text>
        </Space>
        {loading && <Spin size="small" />}
      </div>
      <div ref={containerRef} style={{ flex: 1, minHeight: 0, overflow: 'hidden', border: '1px solid var(--border-color)', borderRadius: 6, background: 'var(--bg-content)' }}>
        <Table
          dataSource={pagedDataSource}
          columns={tableColumns}
          pagination={{
            current: page,
            pageSize: pageSize,
            total: dataSource.length,
            showSizeChanger: true,
            showQuickJumper: true,
            pageSizeOptions: ['20', '50', '100', '200'],
            size: 'small',
            onChange: (p, ps) => { setPage(p); setPageSize(ps); },
            showTotal: (total) => `共 ${total} 行`,
          }}
          size="small"
          bordered
          scroll={{ x: scrollX, y: tableHeight > 0 ? tableHeight : 300 }}
        />
      </div>

      <Modal
        title="编辑打点关系详情"
        open={editOpen}
        onCancel={() => setEditOpen(false)}
        onOk={handleEditSave}
        width={680}
        destroyOnHidden
      >
        <Form form={editForm} layout="vertical">
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item label="源实体（主数据）">
                <Input value={editMasterEntity ? `${editMasterEntity.name}（${editMasterEntity.code}）` : ''} disabled />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="目标实体（业务活动）">
                <Input value={editActivityEntity ? `${editActivityEntity.name}（${editActivityEntity.code}）` : ''} disabled />
              </Form.Item>
            </Col>
            <Col span={24}>
              <Form.Item name="relation_name" label="关系名称">
                <Input placeholder="为空时自动生成" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="cardinality" label="基数" rules={[{ required: true }]}>
                <Select options={['1:1', '1:N', 'N:1', 'N:N'].map((v) => ({ value: v, label: v }))} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="direction" label="方向" rules={[{ required: true }]}>
                <Select options={[{ value: 'forward', label: '正向' }, { value: 'reverse', label: '反向' }]} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="source_field_name" label="源字段">
                <Input placeholder="如 cust_id" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="target_field_name" label="目标字段">
                <Input placeholder="如 customer_id" />
              </Form.Item>
            </Col>
            <Col span={24}>
              <Form.Item name="join_expr" label="关联说明">
                <Input.TextArea rows={2} placeholder="为空时自动按 源字段 = 目标字段 生成" />
              </Form.Item>
            </Col>
            <Col span={24}>
              <Form.Item name="remark" label="备注">
                <Input.TextArea rows={2} />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>
    </div>
  );
};

export default MatrixCanvas;
