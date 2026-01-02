import React, { useState, useEffect } from 'react';
import { Pie } from 'react-chartjs-2';
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js';

ChartJS.register(ArcElement, Tooltip, Legend);

const DocTypesPieChart = () => {
  const [chartData, setChartData] = useState(null);

  useEffect(() => {
    const fetchDocTypes = async () => {
      try {
        const response = await fetch('http://localhost:8000/get_doc_types/');
        const data = await response.json();
        
        const labels = data.map(item => item.doc_type_predicted.trim());
        const counts = data.map(item => item.count);
        
        setChartData({
          labels: labels,
          datasets: [{
            data: counts,
            backgroundColor: [
              '#FF6384',
              '#36A2EB',
              '#FFCE56',
              '#4BC0C0',
              '#9966FF',
              '#FF9F40'
            ]
          }]
        });
      } catch (error) {
        console.error('Error fetching document types:', error);
      }
    };

    fetchDocTypes();
  }, []);

  const options = {
    responsive: true,
    plugins: {
      title: {
        display: true,
        text: 'Document Types Distribution'
      }
    }
  };

  return (
    <div style={{ width: '400px', height: '400px' }}>
      {chartData ? <Pie data={chartData} options={options} /> : <div>Loading...</div>}
    </div>
  );
};

export default DocTypesPieChart;