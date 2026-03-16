
namespace ExtensionDataSignalR_SampleCode
{
    partial class Form1
    {
        /// <summary>
        /// Required designer variable.
        /// </summary>
        private System.ComponentModel.IContainer components = null;

        /// <summary>
        /// Clean up any resources being used.
        /// </summary>
        /// <param name="disposing">true if managed resources should be disposed; otherwise, false.</param>
        protected override void Dispose(bool disposing)
        {
            if (disposing && (components != null))
            {
                components.Dispose();
            }
            base.Dispose(disposing);
        }

        #region Windows Form Designer generated code

        /// <summary>
        /// Required method for Designer support - do not modify
        /// the contents of this method with the code editor.
        /// </summary>
        private void InitializeComponent()
        {
            this.buttonLoginProd = new System.Windows.Forms.Button();
            this.buttonConnect = new System.Windows.Forms.Button();
            this.buttonClear = new System.Windows.Forms.Button();
            this.messageBox = new System.Windows.Forms.TextBox();
            this.label3 = new System.Windows.Forms.Label();
            this.DatabaseID_textBox = new System.Windows.Forms.TextBox();
            this.label4 = new System.Windows.Forms.Label();
            this.EstimateID_textBox = new System.Windows.Forms.TextBox();
            this.buttonGetExtensionData = new System.Windows.Forms.Button();
            this.buttonCallAPI = new System.Windows.Forms.Button();
            this.SuspendLayout();
            // 
            // buttonLoginProd
            // 
            this.buttonLoginProd.Location = new System.Drawing.Point(12, 45);
            this.buttonLoginProd.Name = "buttonLoginProd";
            this.buttonLoginProd.Size = new System.Drawing.Size(294, 61);
            this.buttonLoginProd.TabIndex = 24;
            this.buttonLoginProd.Text = "Login Production";
            this.buttonLoginProd.UseVisualStyleBackColor = true;
            this.buttonLoginProd.Click += new System.EventHandler(this.buttonLoginProd_Click);
            // 
            // buttonConnect
            // 
            this.buttonConnect.Location = new System.Drawing.Point(12, 348);
            this.buttonConnect.Margin = new System.Windows.Forms.Padding(8, 7, 8, 7);
            this.buttonConnect.Name = "buttonConnect";
            this.buttonConnect.Size = new System.Drawing.Size(325, 55);
            this.buttonConnect.TabIndex = 27;
            this.buttonConnect.Text = "Connect to SignalR";
            this.buttonConnect.UseVisualStyleBackColor = true;
            this.buttonConnect.Click += new System.EventHandler(this.buttonConnect_Click);
            // 
            // buttonClear
            // 
            this.buttonClear.Location = new System.Drawing.Point(1023, 348);
            this.buttonClear.Name = "buttonClear";
            this.buttonClear.Size = new System.Drawing.Size(212, 55);
            this.buttonClear.TabIndex = 30;
            this.buttonClear.Text = "Clear";
            this.buttonClear.UseVisualStyleBackColor = true;
            this.buttonClear.Click += new System.EventHandler(this.buttonClear_Click);
            // 
            // messageBox
            // 
            this.messageBox.Location = new System.Drawing.Point(12, 469);
            this.messageBox.Multiline = true;
            this.messageBox.Name = "messageBox";
            this.messageBox.Size = new System.Drawing.Size(2602, 802);
            this.messageBox.TabIndex = 31;
            // 
            // label3
            // 
            this.label3.AutoSize = true;
            this.label3.Location = new System.Drawing.Point(6, 195);
            this.label3.Name = "label3";
            this.label3.Size = new System.Drawing.Size(223, 32);
            this.label3.TabIndex = 34;
            this.label3.Text = "Database Token";
            // 
            // DatabaseID_textBox
            // 
            this.DatabaseID_textBox.Location = new System.Drawing.Point(362, 195);
            this.DatabaseID_textBox.Name = "DatabaseID_textBox";
            this.DatabaseID_textBox.Size = new System.Drawing.Size(2265, 38);
            this.DatabaseID_textBox.TabIndex = 35;
            // 
            // label4
            // 
            this.label4.AutoSize = true;
            this.label4.Location = new System.Drawing.Point(6, 269);
            this.label4.Name = "label4";
            this.label4.Size = new System.Drawing.Size(302, 32);
            this.label4.TabIndex = 36;
            this.label4.Text = "Encrypted Estimate ID ";
            // 
            // EstimateID_textBox
            // 
            this.EstimateID_textBox.Location = new System.Drawing.Point(362, 269);
            this.EstimateID_textBox.Name = "EstimateID_textBox";
            this.EstimateID_textBox.Size = new System.Drawing.Size(2265, 38);
            this.EstimateID_textBox.TabIndex = 37;
            // 
            // buttonGetExtensionData
            // 
            this.buttonGetExtensionData.Location = new System.Drawing.Point(613, 348);
            this.buttonGetExtensionData.Margin = new System.Windows.Forms.Padding(8, 7, 8, 7);
            this.buttonGetExtensionData.Name = "buttonGetExtensionData";
            this.buttonGetExtensionData.Size = new System.Drawing.Size(368, 55);
            this.buttonGetExtensionData.TabIndex = 38;
            this.buttonGetExtensionData.Text = "Get extension data";
            this.buttonGetExtensionData.UseVisualStyleBackColor = true;
            this.buttonGetExtensionData.Click += new System.EventHandler(this.buttonGetExtensionData_Click);
            // 
            // buttonCallAPI
            // 
            this.buttonCallAPI.Location = new System.Drawing.Point(377, 348);
            this.buttonCallAPI.Margin = new System.Windows.Forms.Padding(8, 7, 8, 7);
            this.buttonCallAPI.Name = "buttonCallAPI";
            this.buttonCallAPI.Size = new System.Drawing.Size(200, 55);
            this.buttonCallAPI.TabIndex = 39;
            this.buttonCallAPI.Text = "Call test API";
            this.buttonCallAPI.UseVisualStyleBackColor = true;
            this.buttonCallAPI.Click += new System.EventHandler(this.buttonCallTestAPI_Click);
            // 
            // Form1
            // 
            this.AutoScaleDimensions = new System.Drawing.SizeF(16F, 31F);
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
            this.AutoSize = true;
            this.ClientSize = new System.Drawing.Size(2623, 1412);
            this.Controls.Add(this.buttonCallAPI);
            this.Controls.Add(this.buttonGetExtensionData);
            this.Controls.Add(this.EstimateID_textBox);
            this.Controls.Add(this.label4);
            this.Controls.Add(this.DatabaseID_textBox);
            this.Controls.Add(this.label3);
            this.Controls.Add(this.messageBox);
            this.Controls.Add(this.buttonClear);
            this.Controls.Add(this.buttonConnect);
            this.Controls.Add(this.buttonLoginProd);
            this.MaximumSize = new System.Drawing.Size(2655, 1500);
            this.Name = "Form1";
            this.Text = "Form1";
            this.ResumeLayout(false);
            this.PerformLayout();

        }

        #endregion
        private System.Windows.Forms.Button buttonLoginProd;
        private System.Windows.Forms.Button buttonConnect;
        private System.Windows.Forms.Button buttonClear;
        private System.Windows.Forms.TextBox messageBox;
        private System.Windows.Forms.Label label3;
        private System.Windows.Forms.TextBox DatabaseID_textBox;
        private System.Windows.Forms.Label label4;
        private System.Windows.Forms.TextBox EstimateID_textBox;
        private System.Windows.Forms.Button buttonGetExtensionData;
        private System.Windows.Forms.Button buttonCallAPI;
    }
}