# Marketplace Operation

A Websoft9 automated operations project for mainstream cloud marketplaces. It maintains listed products more efficiently so users get highly available, usable products and versions.

## Websoft9 at Major Cloud

- **[阿里云](https://market.aliyun.com/store/228399/index.html) / [Alibaba Cloud](https://marketplace.alibabacloud.com/store/2116499.html)**
- **[华为云](https://marketplace.huaweicloud.com/seller/b8f57c06a0f7e39f4e206560e71afd76) / [Huawei Cloud](https://marketplace.huaweicloud.com/intl/seller/791bea8ce08849cf9ae4ec61c27e8435)**
- **[Azure](https://azuremarketplace.microsoft.com/en-us/marketplace/apps?search=websoft9inc)**
- **[AWS](https://aws.amazon.com/marketplace/seller-profile?id=c639a579-182c-4d30-8578-4d4d89fba658)**
- **[Google Cloud](https://console.cloud.google.com/marketplace/browse?filter=partner:Websoft9)**

## AI Collaboration

- Repository guidelines and constraints: [`AGENTS.md`](AGENTS.md)
- Project overview and conventions: [`specs/`](specs/README.md)
- Repository-specific skills: [`skills/`](skills/README.md)
- VS Code MCP configuration: `.vscode/mcp.json` (GitHub MCP uses GitHub OAuth; Playwright MCP requires Node.js/npx)

## For Business

- `site/` is the project [dashboard](https://websoft9.github.io/marketplace), a visual operations data analysis system.
- Multiple workflows automatically check product versions, content, and compliance, then trigger manual decisions and optimization.
- **更新 AWS 商品信息**：创建“Update Marketplace Product”Issue，查看对比，通过 `/offer` 评论修改或请求 AI 优化，再审核、发布并确认结果。详见[操作流程](specs/marketplace-offer-update-workflow.md)。

## For Developer

- `make help` — list development commands.
- `make cli` — enter business commands in an isolated `.venv` (`mk help`).

<!-- marketplace-apps:start -->
## Marketplace 应用对应表

下表列出 `product_en.json` 中的应用及其在各 Marketplace 的商品链接。数据源：[offer.json](https://artifact.websoft9.com/cloud_data/offer.json)、[product_en.json](https://artifact.websoft9.com/appstore/release/catalog/product_en.json)；运行 `mk list --update-readme README.md` 重新生成。

已上架应用：97 个；未上架应用：41 个。

| 应用 | Azure | Azure (by VMLab) | AWS | 阿里云 | Alibaba Cloud | 华为云 | Huawei Cloud |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ActiveMQ |  | [vmlabinc1613642184700.activemq](https://azuremarketplace.microsoft.com/en-us/marketplace/apps/vmlabinc1613642184700.activemq) | [8ow143epbkh8mmcijbhrb76rw](https://aws.amazon.com/marketplace/pp?sku=8ow143epbkh8mmcijbhrb76rw) |  | [sgcmjj00025643](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00025643.html) | [317c31d8-ee31-461e-b780-ffb17d3feb84](https://marketplace.huaweicloud.com/contents/317c31d8-ee31-461e-b780-ffb17d3feb84) |  |
| Activepieces |  |  |  |  | [sgcmjj00025928](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00025928.html) |  |  |
| Akeneo |  |  |  |  | [sgcmjj00035322](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00035322.html) |  |  |
| AnythingLLM |  |  |  |  | [sgcmjj00035325](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00035325.html) |  |  |
| Apache Airflow |  |  | [qy0c6rqyf152lwjyxlpjf51q](https://aws.amazon.com/marketplace/pp?sku=qy0c6rqyf152lwjyxlpjf51q) |  | [sgcmjj00025938](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00025938.html) |  |  |
| Apache Kafka |  | [vmlabinc1613642184700.kafka](https://azuremarketplace.microsoft.com/en-us/marketplace/apps/vmlabinc1613642184700.kafka) |  | [cmjj00043548](https://market.aliyun.com/detail/cmjj00043548) | [sgcmjj00026490](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00026490.html) |  |  |
| ArangoDB |  | [vmlabinc1613642184700.arangodb](https://azuremarketplace.microsoft.com/en-us/marketplace/apps/vmlabinc1613642184700.arangodb) |  |  | [sgcmjj00035327](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00035327.html) |  |  |
| Budibase |  |  | [d2p5fuhaxluqcvzuehgw3aor4](https://aws.amazon.com/marketplace/pp?sku=d2p5fuhaxluqcvzuehgw3aor4) |  |  |  |  |
| Canvas |  |  |  | [cmjj00044447](https://market.aliyun.com/detail/cmjj00044447) | [sgcmjj00025935](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00025935.html) |  |  |
| Chatwoot |  |  | [dj718f03moljnx0ahnsevag1v](https://aws.amazon.com/marketplace/pp?sku=dj718f03moljnx0ahnsevag1v) |  |  |  |  |
| Chroma |  |  |  | [cmjj00052319](https://market.aliyun.com/detail/cmjj00052319) | [sgcmjj00025936](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00025936.html) |  |  |
| ClickHouse |  |  |  |  | [sgcmjj00035309](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00035309.html) |  |  |
| CloudBeaver |  |  | [ctwj9bwnpmt9htz6dji5bhwvh](https://aws.amazon.com/marketplace/pp?sku=ctwj9bwnpmt9htz6dji5bhwvh) |  |  |  |  |
| code-server | [codeserver](https://azuremarketplace.microsoft.com/en-us/marketplace/apps/codeserver) |  | [27feqguydue4x6pxbtqibudtk](https://aws.amazon.com/marketplace/pp?sku=27feqguydue4x6pxbtqibudtk) |  |  |  |  |
| CouchDB | [couchdb](https://azuremarketplace.microsoft.com/en-us/marketplace/apps/couchdb) |  | [4wnq44x18uqw2xvnhu2rbk1c1](https://aws.amazon.com/marketplace/pp?sku=4wnq44x18uqw2xvnhu2rbk1c1) |  |  | [571b9e40-28d4-434a-a7cd-07f2d0a8c63b](https://marketplace.huaweicloud.com/contents/571b9e40-28d4-434a-a7cd-07f2d0a8c63b) |  |
| DeepSeek Harness |  |  |  | [cmjj011282](https://market.aliyun.com/detail/cmjj011282) | [sgcmjj00025915](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00025915.html) |  |  |
| Dify |  |  |  |  |  | [987b40c3-b800-437e-a449-62c1bf1b1d7d](https://marketplace.huaweicloud.com/contents/987b40c3-b800-437e-a449-62c1bf1b1d7d)<br>[e6a0a360-6519-4669-872a-bd261048093d](https://marketplace.huaweicloud.com/contents/e6a0a360-6519-4669-872a-bd261048093d) |  |
| Django |  |  |  | [cmjj013062](https://market.aliyun.com/detail/cmjj013062) | [sgcmjj00025926](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00025926.html) |  |  |
| Dolibarr | [dolibarr](https://azuremarketplace.microsoft.com/en-us/marketplace/apps/dolibarr) |  | [n3ukq73j0l8b3i9tjnuxrk90](https://aws.amazon.com/marketplace/pp?sku=n3ukq73j0l8b3i9tjnuxrk90) |  | [sgcmjj00026556](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00026556.html) |  |  |
| Drupal |  | [vmlabinc1613642184700.drupal](https://azuremarketplace.microsoft.com/en-us/marketplace/apps/vmlabinc1613642184700.drupal) | [6q0fvzxq64ua2so918pw17m2z](https://aws.amazon.com/marketplace/pp?sku=6q0fvzxq64ua2so918pw17m2z) |  | [sgcmjj00026410](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00026410.html) |  |  |
| Elasticsearch |  |  | [zvrec5x4z09py88sq4zsphyd](https://aws.amazon.com/marketplace/pp?sku=zvrec5x4z09py88sq4zsphyd) |  |  |  |  |
| ERPNext |  | [vmlabinc1613642184700.erpnext](https://azuremarketplace.microsoft.com/en-us/marketplace/apps/vmlabinc1613642184700.erpnext) | [29ev5szv6iv3ctcwkhfyjnr17](https://aws.amazon.com/marketplace/pp?sku=29ev5szv6iv3ctcwkhfyjnr17) | [cmjj00044761](https://market.aliyun.com/detail/cmjj00044761) | [sgcmjj00025932](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00025932.html)<br>[sgcmjj00025933](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00025933.html) |  |  |
| EspoCRM |  | [vmlabinc1613642184700.espocrm](https://azuremarketplace.microsoft.com/en-us/marketplace/apps/vmlabinc1613642184700.espocrm) | [dctosvbake30ur7u6joxuh92d](https://aws.amazon.com/marketplace/pp?sku=dctosvbake30ur7u6joxuh92d) |  | [sgcmjj00025649](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00025649.html) |  |  |
| GeoServer |  |  |  |  | [sgcmjj00025621](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00025621.html) |  |  |
| Ghost |  | [vmlabinc1613642184700.ghost](https://azuremarketplace.microsoft.com/en-us/marketplace/apps/vmlabinc1613642184700.ghost) |  |  | [sgcmjj00025680](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00025680.html) |  |  |
| Gitea |  |  | [5l8g4bcetjcoyv91sojw0ezy4](https://aws.amazon.com/marketplace/pp?sku=5l8g4bcetjcoyv91sojw0ezy4) |  | [sgcmjj00035307](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00035307.html) |  |  |
| GitLab | [websoft9inc.devops](https://azuremarketplace.microsoft.com/en-us/marketplace/apps/websoft9inc.devops) | [vmlabinc1613642184700.gitlab](https://azuremarketplace.microsoft.com/en-us/marketplace/apps/vmlabinc1613642184700.gitlab) | [adbzaar3mtcj90ozrum9qywbc](https://aws.amazon.com/marketplace/pp?sku=adbzaar3mtcj90ozrum9qywbc) | [cmjj00036406](https://market.aliyun.com/detail/cmjj00036406) |  | [bd008335-9279-4f25-9216-23ea17102f82](https://marketplace.huaweicloud.com/contents/bd008335-9279-4f25-9216-23ea17102f82) |  |
| GoCD |  |  |  |  | [sgcmjj00025924](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00025924.html) |  |  |
| Grafana | [websoft9inc.data-analytics](https://azuremarketplace.microsoft.com/en-us/marketplace/apps/websoft9inc.data-analytics) | [vmlabinc1613642184700.grafana](https://azuremarketplace.microsoft.com/en-us/marketplace/apps/vmlabinc1613642184700.grafana) | [ai8covbxgfph9u8r0c7pmpixj](https://aws.amazon.com/marketplace/pp?sku=ai8covbxgfph9u8r0c7pmpixj) |  | [sgcmjj00025922](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00025922.html) |  |  |
| Graylog Open |  | [vmlabinc1613642184700.graylog](https://azuremarketplace.microsoft.com/en-us/marketplace/apps/vmlabinc1613642184700.graylog) | [8x5mbxnm3cc6ljvw2y15jh1vr](https://aws.amazon.com/marketplace/pp?sku=8x5mbxnm3cc6ljvw2y15jh1vr) |  | [sgcmjj00035306](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00035306.html) |  |  |
| HAProxy |  | [vmlabinc1613642184700.haproxy](https://azuremarketplace.microsoft.com/en-us/marketplace/apps/vmlabinc1613642184700.haproxy) | [43of0ubgxuf0k88if0noeafl8](https://aws.amazon.com/marketplace/pp?sku=43of0ubgxuf0k88if0noeafl8)<br>[e16iyvd40gcn4zsak80ijzkbz](https://aws.amazon.com/marketplace/pp?sku=e16iyvd40gcn4zsak80ijzkbz)<br>[dxx0ssjdnsqnuzhxsuikwe5gj](https://aws.amazon.com/marketplace/pp?sku=dxx0ssjdnsqnuzhxsuikwe5gj) |  | [sgcmjj00025917](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00025917.html) |  |  |
| HashiCorp Vault |  |  |  |  | [sgcmjj00025618](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00025618.html) |  |  |
| Hermes Agent |  |  |  | [cmjj00038136](https://market.aliyun.com/detail/cmjj00038136) | [sgcmjj00025695](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00025695.html) |  |  |
| InfluxDB |  | [vmlabinc1613642184700.influxdb](https://azuremarketplace.microsoft.com/en-us/marketplace/apps/vmlabinc1613642184700.influxdb) | [1axh81ulzt44bm54pq932lgy3](https://aws.amazon.com/marketplace/pp?sku=1axh81ulzt44bm54pq932lgy3) | [cmjj00048857](https://market.aliyun.com/detail/cmjj00048857) | [sgcmjj00025694](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00025694.html) | [eee0310e-3cf1-4b3e-b011-c5f385bd92b7](https://marketplace.huaweicloud.com/contents/eee0310e-3cf1-4b3e-b011-c5f385bd92b7) |  |
| Jenkins |  | [vmlabinc1613642184700.jenkins](https://azuremarketplace.microsoft.com/en-us/marketplace/apps/vmlabinc1613642184700.jenkins) | [8hskwxszuygtjp035hufrv91s](https://aws.amazon.com/marketplace/pp?sku=8hskwxszuygtjp035hufrv91s) | [cmjj023081](https://market.aliyun.com/detail/cmjj023081) | [sgcmjj00025642](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00025642.html) | [f2606319-67a5-427b-9559-3f18bfe3a0af](https://marketplace.huaweicloud.com/contents/f2606319-67a5-427b-9559-3f18bfe3a0af) |  |
| JFrog Artifactory |  |  |  |  | [sgcmjj00025908](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00025908.html) |  |  |
| Jihu GitLab |  |  |  | [cmjj00042495](https://market.aliyun.com/detail/cmjj00042495) |  |  |  |
| Jitsi Meet |  |  | [opo3ek7hdofdv49n00ssdsbf](https://aws.amazon.com/marketplace/pp?sku=opo3ek7hdofdv49n00ssdsbf) | [cmjj00042592](https://market.aliyun.com/detail/cmjj00042592) |  |  |  |
| JupyterHub |  |  | [1peff06qjsn2sbv5lmidde758](https://aws.amazon.com/marketplace/pp?sku=1peff06qjsn2sbv5lmidde758) | [cmjj00038106](https://market.aliyun.com/detail/cmjj00038106) |  |  |  |
| Laravel |  |  |  | [cmjj00038120](https://market.aliyun.com/detail/cmjj00038120) | [sgcmjj00027091](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00027091.html) |  |  |
| LobeHub |  |  |  |  | [sgcmjj00025937](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00025937.html) |  |  |
| LocalAI |  |  |  |  | [sgcmjj00026147](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00026147.html) |  |  |
| MariaDB |  | [vmlabinc1613642184700.mariadb](https://azuremarketplace.microsoft.com/en-us/marketplace/apps/vmlabinc1613642184700.mariadb) | [8vh6esvj53w2201tifxdubdkm](https://aws.amazon.com/marketplace/pp?sku=8vh6esvj53w2201tifxdubdkm) |  | [sgcmjj00026490](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00026490.html) |  |  |
| Mattermost |  | [vmlabinc1613642184700.mattermost](https://azuremarketplace.microsoft.com/en-us/marketplace/apps/vmlabinc1613642184700.mattermost) | [u652p6twwu12h7t6fz0i6w12](https://aws.amazon.com/marketplace/pp?sku=u652p6twwu12h7t6fz0i6w12) |  | [sgcmjj00035312](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00035312.html) |  |  |
| Mautic |  |  | [4nc0bhor45hi7kk5bml0crt8l](https://aws.amazon.com/marketplace/pp?sku=4nc0bhor45hi7kk5bml0crt8l) |  |  |  |  |
| Metabase |  | [vmlabinc1613642184700.metabase](https://azuremarketplace.microsoft.com/en-us/marketplace/apps/vmlabinc1613642184700.metabase) | [ew5bqg8e58sward2pvcrasaoi](https://aws.amazon.com/marketplace/pp?sku=ew5bqg8e58sward2pvcrasaoi) |  | [sgcmjj00025682](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00025682.html) |  |  |
| Milvus |  |  | [a94rj38oqmaxyw35s9iuwexb9](https://aws.amazon.com/marketplace/pp?sku=a94rj38oqmaxyw35s9iuwexb9) |  | [sgcmjj00025906](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00025906.html) | [b535be06-ebb2-4cf0-bc25-8fd0e19ffe9f](https://marketplace.huaweicloud.com/contents/b535be06-ebb2-4cf0-bc25-8fd0e19ffe9f) |  |
| MongoDB |  | [vmlabinc1613642184700.mongodb](https://azuremarketplace.microsoft.com/en-us/marketplace/apps/vmlabinc1613642184700.mongodb) | [2rtop5e31bwj807z83wyj9a9a](https://aws.amazon.com/marketplace/pp?sku=2rtop5e31bwj807z83wyj9a9a) |  | [sgcmjj00035302](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00035302.html) |  |  |
| Moodle |  | [vmlabinc1613642184700.moodle](https://azuremarketplace.microsoft.com/en-us/marketplace/apps/vmlabinc1613642184700.moodle) | [4w9202i1op8rmobk4ggvwmcpf](https://aws.amazon.com/marketplace/pp?sku=4w9202i1op8rmobk4ggvwmcpf) | [cmjj00062730](https://market.aliyun.com/detail/cmjj00062730)<br>[cmjj00038194](https://market.aliyun.com/detail/cmjj00038194) | [sgcmjj00035225](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00035225.html) | [c375a3fb-92a2-4a01-ba54-dfc0f8e2fca6](https://marketplace.huaweicloud.com/contents/c375a3fb-92a2-4a01-ba54-dfc0f8e2fca6)<br>[79bff8d1-7508-4916-bdcf-3059cfb8645f](https://marketplace.huaweicloud.com/contents/79bff8d1-7508-4916-bdcf-3059cfb8645f) |  |
| MySQL |  | [vmlabinc1613642184700.mysql](https://azuremarketplace.microsoft.com/en-us/marketplace/apps/vmlabinc1613642184700.mysql) | [di2jgor4gvf5hbl5m9za88ojj](https://aws.amazon.com/marketplace/pp?sku=di2jgor4gvf5hbl5m9za88ojj) |  | [sgcmjj00025602](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00025602.html) | [edf86504-8e85-4cae-a569-901c92151496](https://marketplace.huaweicloud.com/contents/edf86504-8e85-4cae-a569-901c92151496) |  |
| n8n |  |  |  | [cmjj010920](https://market.aliyun.com/detail/cmjj010920) | [sgcmjj00035305](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00035305.html) | [e1b55beb-bcf4-4fdc-8e1e-4c3478a93bc0](https://marketplace.huaweicloud.com/contents/e1b55beb-bcf4-4fdc-8e1e-4c3478a93bc0) |  |
| Neo4j |  | [vmlabinc1613642184700.neo4j](https://azuremarketplace.microsoft.com/en-us/marketplace/apps/vmlabinc1613642184700.neo4j) | [41lrf78dn9pkhkm4a3pfaxmmk](https://aws.amazon.com/marketplace/pp?sku=41lrf78dn9pkhkm4a3pfaxmmk) | [cmjj00038131](https://market.aliyun.com/detail/cmjj00038131) | [sgcmjj00025623](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00025623.html) | [dba703eb-2552-4249-9d8e-8f0c98eed9ec](https://marketplace.huaweicloud.com/contents/dba703eb-2552-4249-9d8e-8f0c98eed9ec) |  |
| Next.js |  |  |  | [cmjj00039214](https://market.aliyun.com/detail/cmjj00039214) | [sgcmjj00026486](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00026486.html) |  |  |
| Nextcloud Hub | [websoft9inc.ecm](https://azuremarketplace.microsoft.com/en-us/marketplace/apps/websoft9inc.ecm) | [vmlabinc1613642184700.nextcloud](https://azuremarketplace.microsoft.com/en-us/marketplace/apps/vmlabinc1613642184700.nextcloud) | [1e4m2v7hsjoylxwby8prbn0p8](https://aws.amazon.com/marketplace/pp?sku=1e4m2v7hsjoylxwby8prbn0p8) | [cmjj00043872](https://market.aliyun.com/detail/cmjj00043872) | [sgcmjj00035308](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00035308.html) | [cfa2fa60-f72a-4c5f-8119-39cf0a4b5a28](https://marketplace.huaweicloud.com/contents/cfa2fa60-f72a-4c5f-8119-39cf0a4b5a28) |  |
| Node-RED |  |  |  |  | [sgcmjj00025930](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00025930.html) |  |  |
| Odoo | [websoft9inc.digital-transformation](https://azuremarketplace.microsoft.com/en-us/marketplace/apps/websoft9inc.digital-transformation) | [vmlabinc1613642184700.odoo](https://azuremarketplace.microsoft.com/en-us/marketplace/apps/vmlabinc1613642184700.odoo) | [68t98zxjrrxwzhpeetf7bkapc](https://aws.amazon.com/marketplace/pp?sku=68t98zxjrrxwzhpeetf7bkapc) | [cmjj016916](https://market.aliyun.com/detail/cmjj016916)<br>[cmjj00041093](https://market.aliyun.com/detail/cmjj00041093) | [sgcmjj00025939](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00025939.html)<br>[sgcmjj00025650](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00025650.html) | [ce6b0b70-f87d-43d5-be25-77af8cb3e76c](https://marketplace.huaweicloud.com/contents/ce6b0b70-f87d-43d5-be25-77af8cb3e76c) |  |
| Ollama |  |  |  |  |  | [31b19c4c-de39-479c-8d1e-165d37066a96](https://marketplace.huaweicloud.com/contents/31b19c4c-de39-479c-8d1e-165d37066a96) |  |
| ONLYOFFICE Docs |  | [vmlabinc1613642184700.onlyoffice-document-server](https://azuremarketplace.microsoft.com/en-us/marketplace/apps/vmlabinc1613642184700.onlyoffice-document-server) | [2rq7391l2wzbe9oz5w3vcwfmf](https://aws.amazon.com/marketplace/pp?sku=2rq7391l2wzbe9oz5w3vcwfmf) | [cmjj00044586](https://market.aliyun.com/detail/cmjj00044586) |  | [ed39eaa4-1254-470a-9c10-8928f6fa11f7](https://marketplace.huaweicloud.com/contents/ed39eaa4-1254-470a-9c10-8928f6fa11f7) |  |
| Open WebUI |  |  | [63fr1wi2ca50r5u1mup39jypq](https://aws.amazon.com/marketplace/pp?sku=63fr1wi2ca50r5u1mup39jypq) |  |  |  |  |
| OpenClaw |  |  | [9ny9ekqvpxhna8na3pl88boro](https://aws.amazon.com/marketplace/pp?sku=9ny9ekqvpxhna8na3pl88boro) | [cmjj00038326](https://market.aliyun.com/detail/cmjj00038326) |  |  |  |
| OpenDesign |  |  |  |  | [sgcmjj00026127](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00026127.html) |  |  |
| OpenHands |  |  |  |  | [sgcmjj00025916](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00025916.html) |  |  |
| OpenSearch |  |  |  |  |  | [6ea91179-567b-4f3c-9cc1-dcbe0cbb0fd6](https://marketplace.huaweicloud.com/contents/6ea91179-567b-4f3c-9cc1-dcbe0cbb0fd6) |  |
| Portainer |  | [vmlabinc1613642184700.docker](https://azuremarketplace.microsoft.com/en-us/marketplace/apps/vmlabinc1613642184700.docker) | [7wn88yabvv2uxlujuukzftim](https://aws.amazon.com/marketplace/pp?sku=7wn88yabvv2uxlujuukzftim) | [cmjj013064](https://market.aliyun.com/detail/cmjj013064)<br>[cmjj00038369](https://market.aliyun.com/detail/cmjj00038369)<br>[cmjj00038196](https://market.aliyun.com/detail/cmjj00038196)<br>[cmjj00038707](https://market.aliyun.com/detail/cmjj00038707)<br>[cmjj00038102](https://market.aliyun.com/detail/cmjj00038102)<br>[cmjj00039334](https://market.aliyun.com/detail/cmjj00039334) | [sgcmjj00025681](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00025681.html) | [45abbb7d-c55e-4898-a835-5ffe57eb4d9d](https://marketplace.huaweicloud.com/contents/45abbb7d-c55e-4898-a835-5ffe57eb4d9d)<br>[de2f5ea7-6fc8-4307-a3ac-863092e30b79](https://marketplace.huaweicloud.com/contents/de2f5ea7-6fc8-4307-a3ac-863092e30b79)<br>[eedb12d7-30b9-46f4-bec7-630a04ace30d](https://marketplace.huaweicloud.com/contents/eedb12d7-30b9-46f4-bec7-630a04ace30d)<br>[35b162c9-8742-4733-a2d9-df21cbe06a46](https://marketplace.huaweicloud.com/contents/35b162c9-8742-4733-a2d9-df21cbe06a46)<br>[d2d89967-0b7e-4336-b5fd-e54ac847b638](https://marketplace.huaweicloud.com/contents/d2d89967-0b7e-4336-b5fd-e54ac847b638)<br>[126fc304-9edf-47d9-b877-94cf0546f35f](https://marketplace.huaweicloud.com/contents/126fc304-9edf-47d9-b877-94cf0546f35f) |  |
| PostgreSQL | [websoft9inc.dbs](https://azuremarketplace.microsoft.com/en-us/marketplace/apps/websoft9inc.dbs) | [vmlabinc1613642184700.postgresql](https://azuremarketplace.microsoft.com/en-us/marketplace/apps/vmlabinc1613642184700.postgresql) | [1bq0kpm0gaukj9ezxensq887n](https://aws.amazon.com/marketplace/pp?sku=1bq0kpm0gaukj9ezxensq887n) | [cmjj00059560](https://market.aliyun.com/detail/cmjj00059560) | [sgcmjj00026423](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00026423.html) |  |  |
| Prestashop | [websoft9inc.ecommerce](https://azuremarketplace.microsoft.com/en-us/marketplace/apps/websoft9inc.ecommerce) | [vmlabinc1613642184700.prestashop](https://azuremarketplace.microsoft.com/en-us/marketplace/apps/vmlabinc1613642184700.prestashop) | [3ngk4kx1mipobsnmd8ld9re2u](https://aws.amazon.com/marketplace/pp?sku=3ngk4kx1mipobsnmd8ld9re2u) | [cmjj00038197](https://market.aliyun.com/detail/cmjj00038197) | [sgcmjj00025679](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00025679.html) |  |  |
| Prometheus |  |  |  | [cmjj00038195](https://market.aliyun.com/detail/cmjj00038195) | [sgcmjj00026468](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00026468.html) |  |  |
| QwenPaw Hub |  |  |  |  | [sgcmjj00025923](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00025923.html) |  |  |
| RabbitMQ |  | [vmlabinc1613642184700.rabbitmq](https://azuremarketplace.microsoft.com/en-us/marketplace/apps/vmlabinc1613642184700.rabbitmq) | [er8i7izvcdzv9ko6d5lpt06fb](https://aws.amazon.com/marketplace/pp?sku=er8i7izvcdzv9ko6d5lpt06fb)<br>[9dtw38jhpre5n4f7txralg94i](https://aws.amazon.com/marketplace/pp?sku=9dtw38jhpre5n4f7txralg94i) | [cmjj011785](https://market.aliyun.com/detail/cmjj011785) |  | [daf0c560-6490-42a5-9596-82702da171e4](https://marketplace.huaweicloud.com/contents/daf0c560-6490-42a5-9596-82702da171e4) |  |
| Rancher |  |  |  |  | [sgcmjj00025929](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00025929.html) |  |  |
| Redis |  |  | [742wewm4pxr3mpa25y0qcmy3j](https://aws.amazon.com/marketplace/pp?sku=742wewm4pxr3mpa25y0qcmy3j) |  | [sgcmjj00025689](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00025689.html) |  |  |
| Redmine |  | [vmlabinc1613642184700.redmine](https://azuremarketplace.microsoft.com/en-us/marketplace/apps/vmlabinc1613642184700.redmine) | [cq89heybjt2c092zpxyfc2te2](https://aws.amazon.com/marketplace/pp?sku=cq89heybjt2c092zpxyfc2te2) |  | [sgcmjj00025688](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00025688.html) |  |  |
| Rundeck |  |  |  |  | [sgcmjj00025909](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00025909.html) |  |  |
| Seafile |  |  |  |  | [sgcmjj00025925](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00025925.html) |  |  |
| Selenium |  |  |  |  | [sgcmjj00025651](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00025651.html) |  |  |
| Semaphore UI |  |  | [29rzbn98jhqze3laalt64g1fx](https://aws.amazon.com/marketplace/pp?sku=29rzbn98jhqze3laalt64g1fx) |  | [sgcmjj00025934](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00025934.html) |  |  |
| SonarQube |  |  |  | [cmjj00041094](https://market.aliyun.com/detail/cmjj00041094) | [sgcmjj00026014](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00026014.html) |  |  |
| Spring Boot |  |  |  | [cmjj013121](https://market.aliyun.com/detail/cmjj013121) | [sgcmjj00027090](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00027090.html) |  |  |
| SQL Server Express |  |  | [h1jc8n45yx8z82tckmegf513](https://aws.amazon.com/marketplace/pp?sku=h1jc8n45yx8z82tckmegf513) |  |  |  |  |
| Strapi |  |  | [devybqnyxipq37o6gkxvo1og3](https://aws.amazon.com/marketplace/pp?sku=devybqnyxipq37o6gkxvo1og3) |  | [sgcmjj00025927](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00025927.html) |  |  |
| Supabase |  |  | [17rjrw6lacypd20uekxw7b93e](https://aws.amazon.com/marketplace/pp?sku=17rjrw6lacypd20uekxw7b93e) | [cmjj00065682](https://market.aliyun.com/detail/cmjj00065682) | [sgcmjj00025697](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00025697.html) |  |  |
| SuperSet |  | [vmlabinc1613642184700.superset](https://azuremarketplace.microsoft.com/en-us/marketplace/apps/vmlabinc1613642184700.superset) | [cym2dzg7o9d0p7ns9dc1cfc8m](https://aws.amazon.com/marketplace/pp?sku=cym2dzg7o9d0p7ns9dc1cfc8m) | [cmjj00040243](https://market.aliyun.com/detail/cmjj00040243) | [sgcmjj00025684](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00025684.html) | [e1c7aa36-a725-4c6c-b222-cc233304be6d](https://marketplace.huaweicloud.com/contents/e1c7aa36-a725-4c6c-b222-cc233304be6d) |  |
| Teleport |  |  |  |  | [sgcmjj00035301](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00035301.html) |  |  |
| TensorFlow |  | [vmlabinc1613642184700.tensorflow](https://azuremarketplace.microsoft.com/en-us/marketplace/apps/vmlabinc1613642184700.tensorflow) |  | [cmjj00038118](https://market.aliyun.com/detail/cmjj00038118) | [sgcmjj00025683](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00025683.html) |  |  |
| Typesense |  |  |  |  | [sgcmjj00026105](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00026105.html) |  |  |
| Typo3 |  |  | [9mk0cfpgrqz36opfks0h3n9m5](https://aws.amazon.com/marketplace/pp?sku=9mk0cfpgrqz36opfks0h3n9m5) |  | [sgcmjj00031178](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00031178.html) |  |  |
| Umbraco |  |  |  |  | [sgcmjj00031076](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00031076.html) |  |  |
| Vaultwarden |  |  |  |  | [sgcmjj00025619](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00025619.html) |  |  |
| Vespa |  |  |  |  | [sgcmjj00025698](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00025698.html) |  |  |
| Wazuh |  |  |  |  | [sgcmjj00035317](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00035317.html) |  |  |
| Weaviate |  |  |  |  | [sgcmjj00025620](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00025620.html) |  |  |
| WooCommerce |  |  |  | [cmjj011415](https://market.aliyun.com/detail/cmjj011415) |  |  |  |
| WordPress | [websoft9inc.martech](https://azuremarketplace.microsoft.com/en-us/marketplace/apps/websoft9inc.martech) | [vmlabinc1613642184700.wordpress](https://azuremarketplace.microsoft.com/en-us/marketplace/apps/vmlabinc1613642184700.wordpress)<br>[vmlabinc1613642184700.wordpress-websites](https://azuremarketplace.microsoft.com/en-us/marketplace/apps/vmlabinc1613642184700.wordpress-websites) | [6juf4omtss002tppg07lwko9u](https://aws.amazon.com/marketplace/pp?sku=6juf4omtss002tppg07lwko9u)<br>[60a4t9yyr7tg5lk3bg149jj0k](https://aws.amazon.com/marketplace/pp?sku=60a4t9yyr7tg5lk3bg149jj0k)<br>[ct42l4zz1mth7u5nvxkcn5kty](https://aws.amazon.com/marketplace/pp?sku=ct42l4zz1mth7u5nvxkcn5kty) | [cmjj023845](https://market.aliyun.com/detail/cmjj023845)<br>[cmjj010728](https://market.aliyun.com/detail/cmjj010728)<br>[cmjj00041704](https://market.aliyun.com/detail/cmjj00041704)<br>[cmjj011415](https://market.aliyun.com/detail/cmjj011415) | [sgcmjj00035342](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00035342.html)<br>[sgcmjj00035310](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00035310.html)<br>[sgcmjj00025557](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00025557.html) | [472c623a-7ff8-455a-a077-08aa7b389833](https://marketplace.huaweicloud.com/contents/472c623a-7ff8-455a-a077-08aa7b389833)<br>[93b8160a-f4ab-4980-96c3-1eb755a25621](https://marketplace.huaweicloud.com/contents/93b8160a-f4ab-4980-96c3-1eb755a25621)<br>[2e48bae9-32b0-433b-8aef-5d281d59818e](https://marketplace.huaweicloud.com/contents/2e48bae9-32b0-433b-8aef-5d281d59818e)<br>[5875f506-bbb1-4d07-88b2-4c914f02d4a6](https://marketplace.huaweicloud.com/contents/5875f506-bbb1-4d07-88b2-4c914f02d4a6)<br>[6f062599-22e2-41c2-9c62-f48c2ab88065](https://marketplace.huaweicloud.com/contents/6f062599-22e2-41c2-9c62-f48c2ab88065) |  |
| YouTrack |  |  |  |  | [sgcmjj00025931](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00025931.html) |  |  |
| Zammad |  |  |  |  | [sgcmjj00026763](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00026763.html) |  |  |
| Zentao |  |  |  |  | [sgcmjj00025690](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00025690.html) |  |  |
| Zulip |  |  |  |  | [sgcmjj00025918](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00025918.html) |  |  |

### 未在 Marketplace 找到商品的应用

- AFFiNE
- Airbyte
- Alfresco
- Apache NiFi
- APEX
- Caddy
- CKAN
- Consul
- Couchbase
- Directus
- Docker registry
- Elastic Kibana
- Elastic Logstash
- Home Assistant
- inngest
- Jellyfin
- Jitsu
- Keycloak
- Kong Gateway (OSS)
- Langfuse
- LibreChat
- LiteLLM
- Matomo Analytics
- Meilisearch
- MLflow
- nopCommerce
- Oracle Database
- pgAdmin
- phpMyAdmin
- PocketBase
- RedisInsight
- Redpanda Console
- TeamCity
- ThingsBoard
- Traefik Proxy
- Trivy
- Umami
- Uptime Kuma
- Varnish
- WordPress Pro
- XWiki

### Marketplace 商品目录之外的应用

以下应用在 `offer.json` 中存在商品，但 `product_en.json` 中没有对应的 Trademark。

| 应用 | Azure | Azure (by VMLab) | AWS | 阿里云 | Alibaba Cloud | 华为云 | Huawei Cloud |
| --- | --- | --- | --- | --- | --- | --- | --- |
| joomla |  | [vmlabinc1613642184700.joomla](https://azuremarketplace.microsoft.com/en-us/marketplace/apps/vmlabinc1613642184700.joomla) |  |  |  |  |  |
| magento |  | [vmlabinc1613642184700.magento](https://azuremarketplace.microsoft.com/en-us/marketplace/apps/vmlabinc1613642184700.magento) |  |  |  |  |  |
| mediawiki |  | [vmlabinc1613642184700.mediawiki](https://azuremarketplace.microsoft.com/en-us/marketplace/apps/vmlabinc1613642184700.mediawiki) |  |  |  |  |  |
| nodejs | [nodejs](https://azuremarketplace.microsoft.com/en-us/marketplace/apps/nodejs) |  | [369jyztng818eqq1d5a6hz7y4](https://aws.amazon.com/marketplace/pp?sku=369jyztng818eqq1d5a6hz7y4) |  | [sgcmjj00026126](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00026126.html) |  |  |
| pgvector |  |  |  | [cmjj00060251](https://market.aliyun.com/detail/cmjj00060251) | [sgcmjj00026041](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00026041.html) |  |  |
| qdrant |  |  |  |  | [sgcmjj00026107](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00026107.html) |  |  |
| timescaledb |  |  |  |  | [sgcmjj00026412](https://marketplace.alibabacloud.com/products/201072001/sgcmjj00026412.html) |  |  |
| tomcat |  |  | [cg0c50kyelios7mprtu9l641d](https://aws.amazon.com/marketplace/pp?sku=cg0c50kyelios7mprtu9l641d) | [cmjj010920](https://market.aliyun.com/detail/cmjj010920) |  |  |  |
<!-- marketplace-apps:end -->
