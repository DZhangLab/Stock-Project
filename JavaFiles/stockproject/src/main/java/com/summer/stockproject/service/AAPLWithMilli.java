package com.summer.stockproject.service;

import com.summer.stockproject.dao.IntradayBarRepository;
import com.summer.stockproject.entity.IntradayBar;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.util.List;

public class AAPLWithMilli implements IntradayBarService{

    private IntradayBarRepository intradayBarRepository;
    @Override
    public List<IntradayBar> findAll() {
        return null;
    }

    @Override
    public IntradayBar getByTimePoint(LocalDateTime timepoint) {
        return null;
    }

    @Override
    public IntradayBar getById(int theid) {
        return null;
    }

    @Override
    public List<IntradayBar> findByStartDateBetween(Timestamp start, Timestamp end) {

        List<IntradayBar> temp = intradayBarRepository.findByStartDateBetween(start, end);

        for (int i = 0; i < temp.size(); i++ ) {
            long time = temp.get(i).getTimePoint().getTime();

        }




        return null;
    }

    @Override
    public List<IntradayBar> findBySingleDate(Timestamp date) {
        return null;
    }

    @Override
    public List<IntradayBar> universalfind(String tablename, Timestamp start, Timestamp end) {
        return null;
    }

    @Override
    public Timestamp getLatestTimePoint(String tablename) {
        return null;
    }
}
