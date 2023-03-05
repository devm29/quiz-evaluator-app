import React from 'react';
import Quiz from '../components/quiz.js';
import { Route, Routes } from 'react-router-dom';



export const AllRoutes = () => {
    return (
      <div>
         <Routes>
          <Route path="/" element={<Quiz />} />
        </Routes>
      </div>
    );
  };