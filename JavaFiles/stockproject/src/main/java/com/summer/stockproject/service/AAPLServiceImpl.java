package com.summer.stockproject.service;

import com.summer.stockproject.dao.AAPLRepository;
import com.summer.stockproject.entity.AAPL;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.util.Date;
import java.util.List;

@Service
public class AAPLServiceImpl implements AAPLService {

    private AAPLRepository aAPLRepository;

    @Autowired
    public AAPLServiceImpl(AAPLRepository AAPLRepository) {
        this.aAPLRepository = AAPLRepository;
    }

//    @Override
//    public List<AAPL> findBystartDateBetween(Date start, Date end) {
//
//        return  aAPLRepository.findByStartDateBetween(start, end);
//    }

    @Override
    public List<AAPL> findAll() {
        return aAPLRepository.findAll();
    }

    @Override
    public AAPL getByTimePoint(LocalDateTime timepoint) {
        return aAPLRepository.getByTimePoint(timepoint);
    }

    @Override
    public AAPL getById(int theid) {
        return aAPLRepository.getById(theid);
    }

    @Override
    public List<AAPL> findByStartDateBetween(Timestamp start, Timestamp end) {
        return aAPLRepository.findByStartDateBetween(start,end);
    }

    @Override
    public List<AAPL> findBySingleDate(Timestamp date) {
        return aAPLRepository.findBySingleDate(date);
    }

    @Override
    public List<AAPL> universalfind(String tablename, Timestamp date) {
        return aAPLRepository.universalfind(tablename, date);
    }


}
