import React, { useState } from 'react';
import {
  Card, Button, Space, Typography, Badge, List, message,
  Descriptions, Spin, Empty, Steps
} from 'antd';
import {
  BugOutlined, StepForwardOutlined, StopOutlined
} from '@ant-design/icons';
import { skillV2Api } from '../services/skillV2Api';
import { StatusTag } from './shell';

const { Text, Title } = Typography;
const { Step } = Steps;

interface DebugPanelProps {
  skillId: string;
  skillCode: string;
  inputPayload?: Record<string, any>;
}

const DebugPanel: React.FC<DebugPanelProps> = ({ skillId, skillCode, inputPayload = {} }) => {
  const [sessionCode, setSessionCode] = useState<string | null>(null);
  const [sessionStatus, setSessionStatus] = useState<string>('idle');
  const [loading, setLoading] = useState(false);
  const [stepResult, setStepResult] = useState<any>(null);
  const [variables, setVariables] = useState<any>(null);
  const [logs, setLogs] = useState<any[]>([]);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [totalSteps, setTotalSteps] = useState(0);

  const createSession = async () => {
    setLoading(true);
    try {
      const res = await skillV2Api.createDebugSession({
        skill_id: skillId,
        input_payload: inputPayload,
        debug_mode: 'step',
      });
      const code = res.data?.data?.session_code;
      setSessionCode(code || null);
      setSessionStatus('active');
      setStepResult(null);
      setVariables(null);
      setLogs([]);
      setCurrentStepIndex(0);
      message.success('调试会话已创建');
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '创建调试会话失败');
    } finally {
      setLoading(false);
    }
  };

  const doStep = async () => {
    if (!sessionCode) return;
    setLoading(true);
    try {
      const res = await skillV2Api.debugStep(sessionCode);
      const data = res.data?.data;
      setStepResult(data);
      if (data?.phase) setSessionStatus(data.phase);
      if (data?.current_step !== undefined) setCurrentStepIndex(data.current_step);
      if (data?.total_steps !== undefined) setTotalSteps(data.total_steps);

      // 刷新变量和日志
      const [varRes, logRes] = await Promise.all([
        skillV2Api.getDebugVariables(sessionCode),
        skillV2Api.getDebugLogs(sessionCode),
      ]);
      setVariables(varRes.data?.data);
      setLogs(logRes.data?.data || []);

      if (data?.success) {
        message.success(`步骤 ${data.current_step || ''} 完成`);
      }
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '步进失败');
    } finally {
      setLoading(false);
    }
  };

  const terminate = async () => {
    if (!sessionCode) return;
    try {
      await skillV2Api.terminateDebugSession(sessionCode);
      setSessionStatus('terminated');
      message.success('调试会话已终止');
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '终止失败');
    }
  };

  const statusBadge = (status: string) => {
    const colors: Record<string, string> = {
      idle: 'default',
      active: 'processing',
      stepping: 'processing',
      ready: 'warning',
      completed: 'success',
      terminated: 'default',
      error: 'error',
    };
    return <Badge status={colors[status] as any} text={status} />;
  };

  return (
    <Card
      title={
        <Space>
          <BugOutlined style={{ color: 'var(--color-error)' }} />
          <Title level={5} style={{ margin: 0 }}>调试面板</Title>
          {sessionStatus !== 'idle' && statusBadge(sessionStatus)}
        </Space>
      }
      size="small"
      extra={
        <Space size="small">
          {!sessionCode ? (
            <Button size="small" type="primary" icon={<BugOutlined />} onClick={createSession} loading={loading}>
              开始调试
            </Button>
          ) : (
            <>
              {sessionStatus !== 'completed' && sessionStatus !== 'terminated' && (
                <Button size="small" icon={<StepForwardOutlined />} onClick={doStep} loading={loading}>
                  步进
                </Button>
              )}
              <Button size="small" icon={<StopOutlined />} danger onClick={terminate}>
                终止
              </Button>
            </>
          )}
        </Space>
      }
    >
      {!sessionCode ? (
        <Empty description="点击开始调试以创建会话" />
      ) : (
        <Spin spinning={loading}>
          <div style={{ marginBottom: 16 }}>
            <Text type="secondary" style={{ fontSize: 12 }}>会话代码: <Text code>{sessionCode}</Text></Text>
            <br />
            <Text type="secondary" style={{ fontSize: 12 }}>技能: {skillCode}</Text>
          </div>

          {totalSteps > 0 && (
            <Steps size="small" current={currentStepIndex - 1} style={{ marginBottom: 16 }}>
              {Array.from({ length: totalSteps }, (_, i) => (
                <Step key={i} title={`步骤 ${i + 1}`} />
              ))}
            </Steps>
          )}

          {stepResult && (
            <Card title="当前步骤结果" size="small" style={{ marginBottom: 12 }}>
              <Descriptions column={1} size="small">
                <Descriptions.Item label="阶段">{stepResult.phase}</Descriptions.Item>
                {stepResult.step_id && (
                  <Descriptions.Item label="步骤ID">{stepResult.step_id}</Descriptions.Item>
                )}
                {stepResult.message && (
                  <Descriptions.Item label="消息">{stepResult.message}</Descriptions.Item>
                )}
              </Descriptions>
              {stepResult.step_result && (
                <div style={{ marginTop: 8 }}>
                  <Text type="secondary" style={{ fontSize: 12 }}>执行结果:</Text>
                  <pre style={{
                    marginTop: 4, padding: 8, background: 'var(--color-success-bg)', borderRadius: 4,
                    fontSize: 12, maxHeight: 200, overflow: 'auto'
                  }}>
                    {JSON.stringify(stepResult.step_result, null, 2)}
                  </pre>
                </div>
              )}
              {stepResult.result && (
                <div style={{ marginTop: 8 }}>
                  <Text type="secondary" style={{ fontSize: 12 }}>最终输出:</Text>
                  <pre style={{
                    marginTop: 4, padding: 8, background: 'var(--color-success-bg)', borderRadius: 4,
                    fontSize: 12, maxHeight: 200, overflow: 'auto'
                  }}>
                    {JSON.stringify(stepResult.result, null, 2)}
                  </pre>
                </div>
              )}
            </Card>
          )}

          {variables && (
            <Card title="变量快照" size="small" style={{ marginBottom: 12 }}>
              <pre style={{
                margin: 0, padding: 8, background: 'var(--color-primary-bg)', borderRadius: 4,
                fontSize: 12, maxHeight: 200, overflow: 'auto'
              }}>
                {JSON.stringify(variables, null, 2)}
              </pre>
            </Card>
          )}

          {logs.length > 0 && (
            <Card title="执行日志" size="small">
              <List
                size="small"
                dataSource={logs}
                renderItem={(log, idx) => (
                  <List.Item key={idx}>
                    <Text style={{ fontSize: 12 }}>
                      <StatusTag preset={log.type === 'step_complete' ? 'success' : 'default'}>{log.type}</StatusTag>
                      {log.step_id && <span style={{ marginLeft: 8 }}>{log.step_id}</span>}
                      {log.timestamp && <span style={{ marginLeft: 8, color: 'var(--text-tertiary)' }}>{log.timestamp}</span>}
                    </Text>
                  </List.Item>
                )}
              />
            </Card>
          )}
        </Spin>
      )}
    </Card>
  );
};

export default DebugPanel;
