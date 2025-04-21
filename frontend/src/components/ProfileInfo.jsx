import React, { useState, useEffect } from "react";
import { Form, Input, Button, Card, message, Space } from "antd";

const ProfileInfo = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchProfile();
  }, []);

  const fetchProfile = async () => {
    try {
      const response = await fetch("/api/user/profile");
      const data = await response.json();
      form.setFieldsValue(data);
    } catch (error) {
      message.error("Failed to load profile");
    }
  };

  const onFinish = async (values) => {
    setLoading(true);
    try {
      const response = await fetch("/api/user/profile", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(values),
      });

      if (response.ok) {
        message.success("Profile updated successfully");
      } else {
        throw new Error("Failed to update profile");
      }
    } catch (error) {
      message.error("Failed to update profile");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card title="Profile Information">
      <Form
        form={form}
        layout="vertical"
        onFinish={onFinish}
        autoComplete="off"
      >
        <Form.Item
          label="Full Name"
          name="full_name"
          rules={[{ required: true, message: "Please input your full name!" }]}
        >
          <Input />
        </Form.Item>

        <Form.Item
          label="Email"
          name="email"
          rules={[
            { required: true, message: "Please input your email!" },
            { type: "email", message: "Please enter a valid email!" },
          ]}
        >
          <Input />
        </Form.Item>

        <Form.Item
          label="SSN"
          name="ssn"
          rules={[
            { required: true, message: "Please input your SSN!" },
            {
              pattern: /^\d{3}-\d{2}-\d{4}$/,
              message: "Please enter a valid SSN (XXX-XX-XXXX)",
            },
          ]}
        >
          <Input />
        </Form.Item>

        <Form.Item label="Business Name" name="business_name">
          <Input />
        </Form.Item>

        <Form.Item label="Business Type" name="business_type">
          <Input />
        </Form.Item>

        <Form.Item label="Address" name="address">
          <Input.TextArea rows={4} />
        </Form.Item>

        <Form.Item
          label="Phone"
          name="phone"
          rules={[
            {
              pattern: /^\+?[\d\s-()]+$/,
              message: "Please enter a valid phone number",
            },
          ]}
        >
          <Input />
        </Form.Item>

        <Form.Item>
          <Button type="primary" htmlType="submit" loading={loading}>
            Save Profile
          </Button>
        </Form.Item>
      </Form>
    </Card>
  );
};

export default ProfileInfo;
