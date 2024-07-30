Data Sources: AlphaVantage API.
Angular Frontend:
 Components:
  :sentiment-chart: Timeseries chart of       stock sentiment score, with rich filtering UI.

Flask Backend:
 Requests:
  :get_sentiment_by_ticker: Executes an SQL query to get article rows filtered by dates and ticker sentiment score.

AWS Deployment:
 Managers:
  :HybridWebsiteManager: Uses the classes below to fully deploy the front and backend of a project to AWS S3, EC2 and RDS (with web-domain registration).

  :S3Manager: Creates (retrieves) an S3 bucket, modifies bucket settings and syncs files.

  :IAMManager: Creates (esnures) IAM roles and policies.
  
  :EC2Manager: Creates (retrieves) an EC2 instance, ensures security groups and permissions, ensures IAM with IAMManager, executes commands with SSH or SSM (i.e. package installs), clones --cone from git subdir (\back), creates and starts services on EC2.

  :RDSManager: Creates ("") RDS, configures security groups and permissions for integration with EC2 client.

  :Route53Manager: setups DNS and alias of a domain to point to an S3 bucket.

  :Route53DomainsManager: Registers a domain on AWS.

  :LocalPostgresManager: Creates (with options) and dumps a deployment table on the local DB, with optional downgrade of the dump to lower Postgres versions.
