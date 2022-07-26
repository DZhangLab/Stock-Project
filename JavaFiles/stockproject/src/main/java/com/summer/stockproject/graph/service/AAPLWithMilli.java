package com.summer.stockproject.graph.service;

import com.summer.stockproject.graph.entity.AAPL;
import com.summer.stockproject.graph.dao.AAPLRepository;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.util.List;

public class AAPLWithMilli implements AAPLService{

    private AAPLRepository aaplRepository;
    @Override
    public List<AAPL> findAll() {
        return null;
    }

    @Override
    public AAPL getByTimePoint(LocalDateTime timepoint) {
        return null;
    }

    @Override
    public AAPL getById(int theid) {
        return null;
    }

    @Override
    public List<AAPL> findByStartDateBetween(Timestamp start, Timestamp end) {

        List<AAPL> temp = aaplRepository.findByStartDateBetween(start, end);

        for (int i = 0; i < temp.size(); i++ ) {
            long time = temp.get(i).getTimePoint().getTime();

        }




        return null;
    }

    @Override
    public List<AAPL> findBySingleDate(Timestamp date) {
        return null;
    }

    @Override
    public List<AAPL> universalfind(String tablename, Timestamp date) {
        return null;
    }
}
