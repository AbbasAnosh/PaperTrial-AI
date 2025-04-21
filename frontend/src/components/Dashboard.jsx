import React, { useState, useEffect } from "react";
import { Layout, Menu, Tabs, Card } from "antd";
import {
  UserOutlined,
  FileOutlined,
  HistoryOutlined,
  SettingOutlined,
} from "@ant-design/icons";
import ProfileInfo from "./ProfileInfo";
import DocumentManager from "./DocumentManager";
import SubmissionTimeline from "./SubmissionTimeline";
import Settings from "./Settings";

const { Content } = Layout;
const { TabPane } = Tabs;

const Dashboard = () => {
  const [activeTab, setActiveTab] = useState("1");

  const tabItems = [
    {
      key: "1",
      label: "Profile Info",
      icon: <UserOutlined />,
      children: <ProfileInfo />,
    },
    {
      key: "2",
      label: "Documents",
      icon: <FileOutlined />,
      children: <DocumentManager />,
    },
    {
      key: "3",
      label: "Submissions",
      icon: <HistoryOutlined />,
      children: <SubmissionTimeline />,
    },
    {
      key: "4",
      label: "Settings",
      icon: <SettingOutlined />,
      children: <Settings />,
    },
  ];

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Content style={{ padding: "24px" }}>
        <Card>
          <Tabs
            defaultActiveKey="1"
            onChange={setActiveTab}
            items={tabItems}
            tabPosition="left"
            style={{ height: "100%" }}
          />
        </Card>
      </Content>
    </Layout>
  );
};

export default Dashboard;
