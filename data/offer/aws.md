
#### Title
```
Odoo on AWS - Preconfigured, Hardened, Ready in Minutes
```

#### Short description
```
Deploy a pre-configured, self-hosted JupyterHub and JupyterLab in minutes. It uses the upstream projects without product-specific forks. Websoft9 Console helps configure HTTPS, backups, monitoring, and upgrades with rollback
```
#### Long description

```
Odoo runs on AWS as a hardened AMI for self-hosted deployment. The Websoft9 Console provides HTTPS, backups, monitoring, upgrades with rollback, and app deployment, modification, and redeployment, plus one-click templates from the built-in app store.

**What is included?**

Odoo Community 20/19/18 for optional, PostgreSQL, pgAdmin, Nginx, Docker, and Websoft9 Console.

**Use Cases**

Sales, CRM, inventory, purchasing, accounting, project management, website, and eCommerce on one server.

**What You Pay For?**

The application itself is free and open source. The software fee covers the Websoft9 Console, operations toolset, and support with a 24-hour response SLA on business days. AWS infrastructure is billed separately.

**Do I need SSH?**
No. Standard setup is completed in the browser. SSH remains available for advanced customization.

**Trademark Statement**

This application is the property of its original owner, who is not affiliated with and does not endorse this image. Independently provided by Websoft9.

**About Odoo**

Odoo is a suite of web-based open-source business apps, including CRM, Website Builder, eCommerce, Warehouse Management, Project Management, Billing & Accounting, Point of Sale, Human Resources, Marketing, Manufacturing, and Purchase Management.

**About Websoft9**

Websoft9 productionizes open-source software on public clouds: official upstream releases, wrapped with our self-developed management panel, operations toolset, and expert support. The result is a self-hosted deployment that is easier to run and maintain.
```

#### Highlights

```
- Official upstream packages in a hardened image, no forks, no lock-in.
- Websoft9 Console: HTTPS, backup, monitoring, and upgrades with rollback; SSH optional.
- Support: 24-hour response SLA on business days.
```

#### Keywords

```
Odoo, Odoo Community Edition, Odoo ERP, Odoo on AWS, Odoo AMI, self-hosted ERP, open source ERP, Odoo 20, Odoo 19, Odoo CRM, Odoo accounting, Odoo inventory, Odoo manufacturing, Odoo eCommerce, Websoft9
```

#### Usage

```
1. Launch the AMI with 1-Click and copy the instance's Public IPv4 address from the EC2 Console.

2. Open https://<EC2_PUBLIC_IP>:9000 and complete the setup wizard — no SSH login, password lookup, or manual password generation.

3. Use the Websoft9 Console to deploy applications, bind domains, enable HTTPS, and manage backups and monitoring. The Console shows the access URL and port for each application.

Note: Allow inbound TCP 80/443 (web/HTTPS) and 9000 (Websoft9 Console); open additional ports such as 9001 only if required by your applications.
```

#### Refunds
```
This product is billed based on actual EC2 instance usage hours. You may terminate your instance at any time to stop all charges. No refunds are issued for partial usage periods already billed. For billing questions or disputes, contact operation@websoft9.com before opening a claim through AWS Marketplace.
```