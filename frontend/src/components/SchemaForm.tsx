import React, { useState, useEffect } from 'react';
import {
  Input, InputNumber, Switch, Select, Row, Col, Card, Typography, Button
} from 'antd';

const { Text } = Typography;
const { TextArea } = Input;
const { Option } = Select;

export interface JSONSchema {
  type?: string;
  title?: string;
  description?: string;
  default?: any;
  enum?: any[];
  const?: any;
  minimum?: number;
  maximum?: number;
  minLength?: number;
  maxLength?: number;
  pattern?: string;
  format?: string;
  properties?: Record<string, JSONSchema>;
  required?: string[];
  items?: JSONSchema;
  anyOf?: JSONSchema[];
  oneOf?: JSONSchema[];
  allOf?: JSONSchema[];
}

interface SchemaFormProps {
  schema: JSONSchema;
  value?: Record<string, any>;
  onChange?: (values: Record<string, any>) => void;
  prefix?: string;
}

const SchemaForm: React.FC<SchemaFormProps> = ({ schema, value = {}, onChange, prefix = '' }) => {
  const [formValues, setFormValues] = useState<Record<string, any>>(value);

  useEffect(() => {
    setFormValues(value);
  }, [value]);

  const handleChange = (key: string, val: any) => {
    const newValues = { ...formValues, [key]: val };
    setFormValues(newValues);
    onChange?.(newValues);
  };

  if (!schema || !schema.properties) {
    return <Text type="secondary">无 Schema 定义</Text>;
  }

  const { properties = {}, required = [] } = schema;

  return (
    <div>
      {Object.entries(properties).map(([key, propSchema]) => (
        <SchemaField
          key={key}
          name={key}
          schema={propSchema}
          value={formValues[key]}
          onChange={(val) => handleChange(key, val)}
          required={required.includes(key)}
          prefix={prefix}
        />
      ))}
    </div>
  );
};

interface SchemaFieldProps {
  name: string;
  schema: JSONSchema;
  value?: any;
  onChange?: (val: any) => void;
  required?: boolean;
  prefix?: string;
}

const SchemaField: React.FC<SchemaFieldProps> = ({ name, schema, value, onChange, required, prefix }) => {
  const label = schema.title || name;
  const desc = schema.description;
  const isRequired = required;

  // 确定最终类型
  let schemaType = schema.type || 'string';
  if (Array.isArray(schemaType)) {
    schemaType = schemaType.find(t => t !== 'null') || 'string';
  }

  // anyOf / oneOf 简化处理：取第一个
  let effectiveSchema = schema;
  if (schema.anyOf && schema.anyOf.length > 0) {
    effectiveSchema = { ...schema, ...schema.anyOf[0] };
  } else if (schema.oneOf && schema.oneOf.length > 0) {
    effectiveSchema = { ...schema, ...schema.oneOf[0] };
  }

  const finalType = effectiveSchema.type || schemaType;

  const renderControl = () => {
    // const
    if (effectiveSchema.const !== undefined) {
      return (
        <div style={{ padding: '4px 0', color: 'var(--text-secondary)' }}>
          <Text code>{JSON.stringify(effectiveSchema.const)}</Text> (固定值)
        </div>
      );
    }

    // enum
    if (effectiveSchema.enum && effectiveSchema.enum.length > 0) {
      return (
        <Select
          value={value !== undefined ? value : effectiveSchema.default}
          onChange={onChange}
          placeholder={`选择 ${label}`}
          style={{ width: '100%' }}
        >
          {effectiveSchema.enum.map((opt: any) => (
            <Option key={JSON.stringify(opt)} value={opt}>{String(opt)}</Option>
          ))}
        </Select>
      );
    }

    switch (finalType) {
      case 'string':
        if (effectiveSchema.format === 'date') {
          return (
            <Input
              type="date"
              value={value || effectiveSchema.default || ''}
              onChange={(e) => onChange?.(e.target.value)}
              placeholder={desc || `输入 ${label}`}
            />
          );
        }
        if (effectiveSchema.format === 'date-time') {
          return (
            <Input
              type="datetime-local"
              value={value || effectiveSchema.default || ''}
              onChange={(e) => onChange?.(e.target.value)}
              placeholder={desc || `输入 ${label}`}
            />
          );
        }
        if ((effectiveSchema.maxLength || 0) > 100) {
          return (
            <TextArea
              rows={3}
              value={value || effectiveSchema.default || ''}
              onChange={(e) => onChange?.(e.target.value)}
              placeholder={desc || `输入 ${label}`}
              maxLength={effectiveSchema.maxLength}
            />
          );
        }
        return (
          <Input
            value={value !== undefined ? value : (effectiveSchema.default || '')}
            onChange={(e) => onChange?.(e.target.value)}
            placeholder={desc || `输入 ${label}`}
          />
        );

      case 'integer':
      case 'number':
        return (
          <InputNumber
            value={value !== undefined ? value : effectiveSchema.default}
            onChange={(val) => onChange?.(val)}
            min={effectiveSchema.minimum}
            max={effectiveSchema.maximum}
            style={{ width: '100%' }}
            placeholder={desc || `输入 ${label}`}
          />
        );

      case 'boolean':
        return (
          <Switch
            checked={value !== undefined ? value : (effectiveSchema.default || false)}
            onChange={(val) => onChange?.(val)}
          />
        );

      case 'array':
        return (
          <ArrayField
            schema={effectiveSchema.items || { type: 'string' }}
            value={value || effectiveSchema.default || []}
            onChange={onChange}
          />
        );

      case 'object':
        return (
          <Card size="small" style={{ background: 'var(--bg-subtle)' }}>
            <SchemaForm
              schema={effectiveSchema}
              value={value || effectiveSchema.default || {}}
              onChange={onChange}
              prefix={`${prefix}${name}.`}
            />
          </Card>
        );

      default:
        return (
          <Input
            value={value || effectiveSchema.default || ''}
            onChange={(e) => onChange?.(e.target.value)}
            placeholder={desc || `输入 ${label}`}
          />
        );
    }
  };

  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ marginBottom: 4, fontWeight: 500 }}>
        {label}
        {isRequired && <span style={{ color: 'var(--color-error)', marginLeft: 4 }}>*</span>}
        {desc && <div style={{ fontSize: 12, color: 'var(--text-tertiary)', fontWeight: 400 }}>{desc}</div>}
      </div>
      {renderControl()}
    </div>
  );
};

interface ArrayFieldProps {
  schema: JSONSchema;
  value: any[];
  onChange?: (val: any[]) => void;
}

const ArrayField: React.FC<ArrayFieldProps> = ({ schema, value, onChange }) => {
  const handleAdd = () => {
    const newVal = [...value, generateDefault(schema)];
    onChange?.(newVal);
  };

  const handleRemove = (idx: number) => {
    const newVal = value.filter((_, i) => i !== idx);
    onChange?.(newVal);
  };

  const handleItemChange = (idx: number, val: any) => {
    const newVal = [...value];
    newVal[idx] = val;
    onChange?.(newVal);
  };

  return (
    <div>
      {value.map((item, idx) => (
        <Row key={idx} gutter={8} align="middle" style={{ marginBottom: 8 }}>
          <Col flex="auto">
            {schema.type === 'object' && schema.properties ? (
              <SchemaForm
                schema={schema}
                value={item}
                onChange={(v) => handleItemChange(idx, v)}
              />
            ) : (
              <SchemaField
                name={`item_${idx}`}
                schema={schema}
                value={item}
                onChange={(v) => handleItemChange(idx, v)}
              />
            )}
          </Col>
          <Col flex="none">
            <Button type="link" danger onClick={() => handleRemove(idx)} style={{ padding: 0 }}>
              删除
            </Button>
          </Col>
        </Row>
      ))}
      <Button type="link" onClick={handleAdd} style={{ padding: 0 }}>
        + 添加项
      </Button>
    </div>
  );
};

function generateDefault(schema: JSONSchema): any {
  if (schema.default !== undefined) return schema.default;
  switch (schema.type) {
    case 'string': return '';
    case 'integer': return 0;
    case 'number': return 0.0;
    case 'boolean': return false;
    case 'array': return [];
    case 'object':
      const obj: Record<string, any> = {};
      if (schema.properties) {
        for (const [k, v] of Object.entries(schema.properties)) {
          if (schema.required?.includes(k)) {
            obj[k] = generateDefault(v);
          }
        }
      }
      return obj;
    default: return null;
  }
}

export default SchemaForm;
